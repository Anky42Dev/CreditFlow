import logging

from django.utils import timezone

from common.tracing import get_tracer
from shared.application.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class _SkipSaga(Exception):
    """Internal control-flow signal: the saga has nothing to do for this
    application (already issued, or no longer APPROVED) — not a failure, so
    it must never trigger compensation."""


class LoanIssuanceSaga:
    """DOC 5 §8.2, Roadmap Этап 3 п.9: ApplicationApproved -> CreateLoan ->
    LoanCreated -> BuildSchedule -> ScheduleBuilt -> MarkDisbursed ->
    NotifyClient, with compensation (-> MANUAL_REVIEW, audited) if any step
    from CreateLoan through MarkDisbursed fails. Invoked by
    apps.outbox.consumers on ApplicationApproved messages drained from the
    broker (apps.outbox.management.commands.consume_events).

    ASSUMPTION (read alongside Этап 2's ASSUMPTIONS on why the legacy services
    still drive persistence): apps.lending.services.disburse_loan already
    performs this exact sequence — create Loan, build the schedule, mark
    DISBURSED, notify — synchronously and *idempotently*
    (`if hasattr(application, "loan"): return application.loan`), called
    inline from apps.applications.services.perform_scoring/approve_application
    (Doc 3 §9.1/§10) before either of those functions returns. Since
    ApplyScoringDecisionUseCase/ApproveApplicationUseCase only write the
    ApplicationApproved outbox row *after* that inline call has already
    returned, by the time the Outbox Relay publishes it and this saga
    consumes it, the Loan has, in the overwhelmingly common case, already
    been created synchronously.

    Rather than removing that inline call (touching apps/lending/services.py
    and apps/applications/services.py beyond the "minimal touch" this stage's
    instructions call for, and re-risking Middle's already-tested
    transactional/audit/notification behaviour), this saga is built as a
    second, independently idempotent path: `_issue` re-checks
    `hasattr(application, "loan")` and bails out via `_SkipSaga` if a Loan
    already exists, so consuming an ApplicationApproved event whose loan was
    already issued synchronously is a safe no-op, not a duplicate
    disbursement. The saga's steps and its BuildSchedule-failure compensation
    (AC-5) are real and independently exercised by tests that hand it an
    APPROVED application with no Loan yet — see
    tests/integration/lending/test_loan_issuance_saga.py. Making this saga the
    *sole* issuance path (retiring the inline disburse_loan call) is
    Follow-up work, out of scope for Этап 3.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def handle(self, payload: dict) -> None:
        # DOC 5 §12.3: one span per saga run — auto-instrumentation can't see
        # this (it runs off a Celery Beat-driven consumer loop, not an HTTP
        # request). trace_id (correlation id threaded via the outbox
        # payload, see apps.outbox.consumers) is attached as an attribute
        # rather than real span-context propagation, since the broker hop
        # doesn't carry W3C trace headers.
        application_id = payload["application_id"]
        with tracer.start_as_current_span(
            "loan_issuance_saga.handle",
            attributes={
                "application_id": application_id,
                "app.trace_id": payload.get("trace_id") or "",
            },
        ):
            try:
                loan = self._issue(application_id)
            except _SkipSaga:
                return
            except Exception as exc:  # noqa: BLE001 - saga step failure triggers compensation
                self._compensate(application_id, exc)
                return
            self._notify_client(loan)

    def _issue(self, application_id: int):
        from apps.applications.models import CreditApplication

        with self.uow:
            application = (
                CreditApplication.objects.select_for_update()
                .select_related("product", "user")
                .get(id=application_id)
            )
            if hasattr(application, "loan"):
                logger.info(
                    "LoanIssuanceSaga: application_id=%s already has a loan — skipping (idempotent)",
                    application_id,
                )
                raise _SkipSaga
            if application.status != "APPROVED":
                logger.warning(
                    "LoanIssuanceSaga: application_id=%s is %s, not APPROVED — skipping",
                    application_id,
                    application.status,
                )
                raise _SkipSaga

            loan = self._create_loan(application)  # CreateLoan -> LoanCreated
            self._build_schedule(loan)  # BuildSchedule -> ScheduleBuilt
            self._mark_disbursed(application)  # MarkDisbursed
            return loan

    def _create_loan(self, application):
        from apps.lending.models import Loan
        from common.metrics import loans_disbursed_amount_total

        loan = Loan.objects.create(
            application=application,
            user=application.user,
            principal=application.amount,
            interest_rate=application.product.interest_rate,
            term_months=application.term_months,
            monthly_payment=application.monthly_payment,
            outstanding_balance=application.amount,
            status="ACTIVE",
            disbursed_at=timezone.now(),
        )
        logger.info(
            "LoanIssuanceSaga: LoanCreated loan_id=%s application_id=%s",
            loan.id,
            application.id,
        )
        loans_disbursed_amount_total.inc(float(loan.principal))  # DOC 5 §12.1
        return loan

    def _build_schedule(self, loan) -> None:
        from apps.lending.models import Transaction
        from apps.lending.services import build_payment_schedule

        build_payment_schedule(loan)
        Transaction.objects.create(
            loan=loan,
            type="DISBURSEMENT",
            amount=loan.principal,
            balance_after=loan.principal,
        )
        logger.info("LoanIssuanceSaga: ScheduleBuilt loan_id=%s", loan.id)

    def _mark_disbursed(self, application) -> None:
        application.status = "DISBURSED"
        application.save(update_fields=["status"])
        logger.info("LoanIssuanceSaga: MarkDisbursed application_id=%s", application.id)

    def _notify_client(self, loan) -> None:
        from apps.notifications.services import notify_user

        notify_user(loan.user, "loan.disbursed", loan)

    def _compensate(self, application_id: int, exc: Exception) -> None:
        """DOC 5 §8.2: 'CreateLoan fail -> ApplicationApprovalFailed -> вернуть
        в MANUAL_REVIEW'. Runs in its own transaction, separate from `_issue`'s
        (which has already rolled back any partial Loan/schedule writes by the
        time this executes) — see AC-5."""
        from apps.applications.models import CreditApplication
        from common.audit import audit_log

        logger.exception(
            "LoanIssuanceSaga: compensating application_id=%s due to %s",
            application_id,
            exc,
        )
        with self.uow:
            application = CreditApplication.objects.select_for_update().get(
                id=application_id
            )
            previous_status = application.status
            application.status = "MANUAL_REVIEW"
            application.save(update_fields=["status"])
            audit_log(
                None,
                "application.approval_failed",
                application,
                changes={
                    "before": previous_status,
                    "after": "MANUAL_REVIEW",
                    "reason": str(exc),
                },
            )
