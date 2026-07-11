from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

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


def perform_scoring(application_id) -> CreditApplication:
    """Doc 3 §6.3. Этап 4 wires disburse_loan on APPROVED; push_status (Этап 5)
    notifies the applicant's WS group after each status change. notify_user
    (email + in-app Notification) remains for Этап 6 — that model doesn't exist yet."""
    from apps.realtime.push import push_status

    application = CreditApplication.objects.select_related("user__profile").get(id=application_id)
    application.status = "SCORING"
    application.save(update_fields=["status"])
    push_status(application)

    score = compute_score(application)
    if score >= SCORE_APPROVED_THRESHOLD:
        decision = "APPROVED"
        reason = "Sufficient income"
    elif score >= SCORE_MANUAL_REVIEW_THRESHOLD:
        decision = "MANUAL_REVIEW"
        reason = "Borderline score, needs underwriter review"
    else:
        decision = "REJECTED"
        reason = "High debt-to-income or missing data"

    ScoringResult.objects.create(application=application, score=score, decision=decision, reason=reason)
    application.status = decision
    application.save(update_fields=["status"])
    push_status(application)

    if decision == "APPROVED":
        from apps.lending.services import disburse_loan

        disburse_loan(application)

    return application
