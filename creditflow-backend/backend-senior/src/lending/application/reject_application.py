from shared.application.outbox import OutboxStore
from shared.application.unit_of_work import UnitOfWork
from shared.application.use_case import UseCase

from ..domain.repositories.application_repository import ApplicationRepository
from ..infrastructure.mappers import ApplicationMapper


class RejectApplicationUseCase(UseCase):
    """DOC 5 §6.1, Roadmap Этап 2 п.5. Wraps apps.applications.services.reject_application
    (Doc 3 §10) — unchanged — in the shared UnitOfWork; see
    SubmitApplicationUseCase's docstring for why the legacy service, not the
    domain aggregate, still drives the mutation this stage, and for the same
    "replay the transition on a pre-mutation aggregate to get pull_events()"
    strategy used here for the Roadmap Этап 3 п.7 outbox write (ApplicationRejected).
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

    def execute(self, application_id: int, reason: str = "", actor=None, request=None):
        from apps.applications.services import reject_application

        with self.uow:
            model = self.repo.get_model(application_id)
            aggregate = ApplicationMapper.to_domain(model)  # pre-mutation (MANUAL_REVIEW)
            model = reject_application(
                model, reason=reason, actor=actor, request=request
            )
            aggregate.reject_from_manual_review()
            self.outbox.append(
                aggregate.pull_events(),
                aggregate_type="CreditApplication",
                aggregate_id=aggregate.id,
            )
        return model
