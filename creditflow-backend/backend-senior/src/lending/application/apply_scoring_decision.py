from shared.application.outbox import OutboxStore
from shared.application.unit_of_work import UnitOfWork
from shared.application.use_case import UseCase

from ..domain.repositories.application_repository import ApplicationRepository
from ..domain.value_objects.application_status import ApplicationStatus
from ..infrastructure.mappers import ApplicationMapper


class ApplyScoringDecisionUseCase(UseCase):
    """DOC 5 §6.1, Roadmap Этап 3 п.7-8. Wraps apps.applications.services.perform_scoring
    (Doc 3 §6.3) — unchanged — in the shared UnitOfWork, using the same
    "replay the transition on a pre-mutation aggregate to get pull_events()"
    strategy as Submit/Approve/RejectApplicationUseCase.

    This use case exists (new in Этап 3, not part of Этап 2's Submit/Approve/
    Reject/Repay set) because perform_scoring — not any Этап 2 use case — is
    where the *automatic* SCORING -> {APPROVED, REJECTED, MANUAL_REVIEW}
    transition actually happens; it's invoked from apps.applications.tasks.
    score_application, the Celery task submit_application.delay()s. Without
    wiring this in, ApplicationApproved/ApplicationRejected would only reach
    the outbox for the *manual* underwriter approve/reject path (Этап 2's
    Approve/RejectApplicationUseCase), never for the (majority) automatic-
    scoring path — leaving Roadmap Этап 3 п.8's "publish ApplicationApproved/
    ApplicationRejected" requirement half-met. apps/applications/tasks.py is
    changed to call this use case via the DI container instead of importing
    perform_scoring directly — a one-line, minimal-touch change mirroring the
    thin-adapter pattern Этап 2 п.6 already applied to the views.

    Decision lookup uses the ScoringResult row perform_scoring creates, not
    model.status: on APPROVED, perform_scoring calls disburse_loan inline
    (Doc 3 §9.1), which moves the application straight past APPROVED to
    DISBURSED before this use case regains control, so `model.status` alone
    can no longer tell us which decision was made. MANUAL_REVIEW raises no
    event, matching CreditApplicationAggregate.apply_scoring_decision and
    Roadmap Этап 3 п.8 (only Submitted/Approved/Rejected go to the broker).
    """

    def __init__(
        self,
        repo: ApplicationRepository,
        uow: UnitOfWork,
        outbox: OutboxStore | None = None,
    ):
        from shared.infrastructure.outbox import DjangoOutboxStore

        self.repo = repo
        self.uow = uow
        self.outbox = outbox or DjangoOutboxStore()

    def execute(self, application_id: int):
        from apps.applications.models import ScoringResult
        from apps.applications.services import perform_scoring

        with self.uow:
            model = self.repo.get_model(application_id)
            aggregate = ApplicationMapper.to_domain(model)  # pre-mutation (SUBMITTED)
            perform_scoring(application_id)

            scoring_result = (
                ScoringResult.objects.filter(application_id=application_id)
                .order_by("-created_at")
                .first()
            )
            aggregate.start_scoring()
            aggregate.apply_scoring_decision(ApplicationStatus(scoring_result.decision))
            self.outbox.append(
                aggregate.pull_events(),
                aggregate_type="CreditApplication",
                aggregate_id=aggregate.id,
            )
            model.refresh_from_db()
        return model
