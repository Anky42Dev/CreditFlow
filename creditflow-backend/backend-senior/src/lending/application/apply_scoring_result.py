import logging

from django.utils import timezone

from shared.application.outbox import OutboxStore
from shared.application.unit_of_work import UnitOfWork
from shared.application.use_case import UseCase

from ..domain.repositories.application_repository import ApplicationRepository
from ..domain.value_objects.application_status import ApplicationStatus
from ..infrastructure.mappers import ApplicationMapper

logger = logging.getLogger(__name__)


class ApplyScoringResultUseCase(UseCase):
    """DOC 5 §6.1/§7, Roadmap Этап 4 п.11: applies a decision computed by the
    external FastAPI scoring_service (delivered as a ScoringCompleted broker
    message, see apps.outbox.consumers._handle_scoring_completed) to the
    CreditApplication — the broker-driven counterpart of
    ApplyScoringDecisionUseCase (Этап 3), which drives the *local* Celery/
    perform_scoring heuristic path instead.

    Idempotency guard: the legacy Celery task (apps.applications.tasks.
    score_application, dispatched synchronously on submit) and this
    broker-driven path both race to score the same SUBMITTED application —
    both are left running in Этап 4 rather than one being torn out (see Этап 4
    report ASSUMPTIONS: removing the Celery path would be a larger, separate,
    behavior-changing task touching the Doc3-level test suite). Whichever
    resolves first wins; if `model.status` is no longer SUBMITTED when this
    use case runs, the ScoringCompleted message is a no-op, not an error —
    the application was already scored by the other path.
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

    def execute(self, application_id: int, score: int, decision: str, reason: str):
        from apps.applications.services import (
            apply_scoring_result,
            transition_to_scoring,
        )
        from common.metrics import scoring_duration_seconds

        with self.uow:
            model = self.repo.get_model(application_id)
            if model.status != "SUBMITTED":
                logger.info(
                    "ApplyScoringResultUseCase: application %s not SUBMITTED "
                    "(status=%s), skipping — already resolved by another "
                    "scoring path",
                    application_id,
                    model.status,
                )
                return model

            aggregate = ApplicationMapper.to_domain(model)  # pre-mutation (SUBMITTED)
            transition_to_scoring(model)
            apply_scoring_result(application_id, score, decision, reason)

            aggregate.start_scoring()
            aggregate.apply_scoring_decision(ApplicationStatus(decision))
            self.outbox.append(
                aggregate.pull_events(),
                aggregate_type="CreditApplication",
                aggregate_id=aggregate.id,
            )
            model.refresh_from_db()
        if model.submitted_at:
            # DOC 5 §12.1: submission -> decision-applied latency, not
            # wall-clock processing time — includes broker/queue wait.
            scoring_duration_seconds.observe(
                (timezone.now() - model.submitted_at).total_seconds()
            )
        return model
