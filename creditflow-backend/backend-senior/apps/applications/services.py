from decimal import Decimal

from django.db.models import F
from django.db.models.functions import ExtractHour, Now
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.audit import audit_log
from common.exceptions import ConflictError

from .models import CreditApplication, ScoringResult

SCORE_APPROVED_THRESHOLD = 700
SCORE_MANUAL_REVIEW_THRESHOLD = 500


def calc_annuity(amount: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    r = annual_rate / Decimal(100) / Decimal(12)
    if r == 0:
        return (amount / months).quantize(Decimal("0.01"))
    factor = (1 + r) ** months
    payment = amount * r * factor / (factor - 1)
    return payment.quantize(Decimal("0.01"))


def validate_amount_and_term(product, amount, term_months) -> None:
    if not (product.min_amount <= amount <= product.max_amount):
        raise ValidationError({"amount": [f"Must be between {product.min_amount} and {product.max_amount}"]})
    if not (product.min_term_months <= term_months <= product.max_term_months):
        raise ValidationError(
            {"term_months": [f"Must be between {product.min_term_months} and {product.max_term_months}"]}
        )


def submit_application(application: CreditApplication) -> CreditApplication:
    """Doc 3 §6.2: submit puts the application in the scoring queue instead of scoring inline."""
    from .tasks import score_application

    if application.status != "DRAFT":
        raise ConflictError(message="Only DRAFT applications can be submitted")

    validate_amount_and_term(application.product, application.amount, application.term_months)

    application.monthly_payment = calc_annuity(
        application.amount, application.product.interest_rate, application.term_months
    )
    application.status = "SUBMITTED"
    application.submitted_at = timezone.now()
    application.save()

    score_application.delay(application.id)
    return application


def compute_score(application: CreditApplication) -> int:
    # getattr, not application.user.profile: a missing Profile row (signal failure,
    # data imported without one) must degrade to "missing data", not crash the task.
    profile = getattr(application.user, "profile", None)
    score = 500
    # Zero and missing income are treated alike (no ratio signal) — a Profile with
    # monthly_income=0 is drawn from the same "no income declared" corpus.
    if profile and profile.monthly_income:
        ratio = application.monthly_payment / profile.monthly_income
        if ratio < Decimal("0.2"):
            score += 300
        elif ratio < Decimal("0.4"):
            score += 100
        else:
            score -= 200
    if not profile or profile.birth_date is None:
        score -= 100
    return max(0, min(1000, score))


def decide(score: int) -> tuple[str, str]:
    """Doc 3 §6.3 decision bucketing, split out of perform_scoring so Этап 4's
    ApplyScoringResultUseCase (score/decision arriving from the external
    scoring_service over the broker) can reuse the exact same thresholds/
    reasons without duplicating them — kept here (not ported to
    scoring_service) since scoring_service has its own, deliberately
    independent copy (its own release cycle, DOC 5 §7.1); this is the
    single source of truth for the *legacy in-process* Celery scoring path.
    """
    if score >= SCORE_APPROVED_THRESHOLD:
        return "APPROVED", "Sufficient income"
    elif score >= SCORE_MANUAL_REVIEW_THRESHOLD:
        return "MANUAL_REVIEW", "Borderline score, needs underwriter review"
    return "REJECTED", "High debt-to-income or missing data"


def transition_to_scoring(application: CreditApplication) -> CreditApplication:
    """Doc 3 §6.3: SUBMITTED -> SCORING. Split out of perform_scoring (Этап 4)
    so ApplyScoringResultUseCase can drive the same transition for
    applications scored by the external scoring_service rather than the
    local Celery task."""
    from apps.realtime.push import push_status

    previous_status = application.status
    application.status = "SCORING"
    application.save(update_fields=["status"])
    audit_log(
        None,
        "application.status_changed",
        application,
        changes={"before": previous_status, "after": "SCORING"},
    )
    push_status(application)
    return application


def apply_scoring_result(application_id, score: int, decision: str, reason: str) -> CreditApplication:
    """Doc 3 §6.3 tail of perform_scoring, split out (Этап 4, Roadmap п.10-11)
    so it can be driven either by the local heuristic (perform_scoring, below)
    or by a decision computed externally by scoring_service and delivered as
    a ScoringCompleted broker message (see
    lending.application.apply_scoring_result.ApplyScoringResultUseCase and
    apps.outbox.consumers._handle_scoring_completed). Assumes the application
    is already in SCORING status (transition_to_scoring, above, or the
    equivalent aggregate transition)."""
    from apps.realtime.push import push_status
    from apps.notifications.services import notify_user

    application = CreditApplication.objects.select_related("user__profile").get(id=application_id)
    ScoringResult.objects.create(application=application, score=score, decision=decision, reason=reason)
    application.status = decision
    application.save(update_fields=["status"])
    audit_log(
        None,
        "application.status_changed",
        application,
        changes={"before": "SCORING", "after": decision},
    )
    push_status(application)
    notify_user(application.user, f"application.{decision.lower()}", application)

    if decision == "APPROVED":
        from apps.lending.services import disburse_loan

        disburse_loan(application)

    return application


def perform_scoring(application_id) -> CreditApplication:
    """Doc 3 §6.3. Этап 4 wires disburse_loan on APPROVED; push_status (Этап 5)
    notifies the applicant's WS group after each status change. notify_user
    (email + in-app Notification) is wired here from Этап 6.

    Doc 3 §14: each status change is written to the AuditLog. These are
    system-initiated (actor=None) since they come from the async scoring task,
    not from a specific user's action."""
    application = CreditApplication.objects.select_related("user__profile").get(id=application_id)
    transition_to_scoring(application)

    score = compute_score(application)
    decision, reason = decide(score)

    return apply_scoring_result(application_id, score, decision, reason)


def approve_application(application: CreditApplication, comment: str = "", actor=None, request=None) -> CreditApplication:
    """Doc 3 §10: admin/underwriter approval — only a MANUAL_REVIEW application can
    be approved this way. Mirrors perform_scoring's APPROVED branch: flips the
    application to APPROVED, then disburse_loan (already idempotent) takes it to
    DISBURSED and builds the payment schedule.

    `actor`/`request` are optional (default None) so existing callers/tests keep
    working; the admin API view passes request.user and request so the
    resulting AuditLog entry records who approved it, from where, and any
    review comment.
    """
    from apps.lending.services import disburse_loan
    from apps.notifications.services import notify_user
    from apps.realtime.push import push_status

    if application.status != "MANUAL_REVIEW":
        raise ConflictError(message="Only MANUAL_REVIEW applications can be approved")

    application.status = "APPROVED"
    application.save(update_fields=["status"])
    audit_log(
        actor,
        "application.approved",
        application,
        changes={"comment": comment},
        request=request,
    )
    push_status(application)
    notify_user(application.user, "application.approved", application)

    disburse_loan(application)
    return application


def reject_application(application: CreditApplication, reason: str = "", actor=None, request=None) -> CreditApplication:
    """Doc 3 §10: admin/underwriter rejection of a MANUAL_REVIEW application.

    `actor`/`request` are optional (default None) for the same reason as in
    approve_application above.
    """
    from apps.notifications.services import notify_user
    from apps.realtime.push import push_status

    if application.status != "MANUAL_REVIEW":
        raise ConflictError(message="Only MANUAL_REVIEW applications can be rejected")

    application.status = "REJECTED"
    application.save(update_fields=["status"])
    audit_log(
        actor,
        "application.rejected",
        application,
        changes={"reason": reason},
        request=request,
    )
    push_status(application)
    notify_user(application.user, "application.rejected", application)
    return application


def request_documents(application: CreditApplication) -> CreditApplication:
    """Doc 3 §10: asks the client for supporting documents. There's no dedicated
    state in the application's status machine for this yet, so it's a
    notification-only action — the application's status is left untouched."""
    from apps.notifications.services import notify_user

    notify_user(application.user, "application.documents_requested", application)
    return application


def underwriter_queue_queryset():
    """Doc 3 §13.1/§13.2: the MANUAL_REVIEW queue an underwriter dashboard would
    sort by staleness. select_related avoids per-row queries for user/profile/
    product, and waiting_hours is annotated in the DB (ExtractHour(Now() -
    submitted_at)) instead of computed per-row in Python, so iterating the
    queryset and reading these fields costs exactly one query."""
    return (
        CreditApplication.objects.filter(status="MANUAL_REVIEW")
        .select_related("user", "user__profile", "product")
        .annotate(waiting_hours=ExtractHour(Now() - F("submitted_at")))
        .order_by("submitted_at")
    )
