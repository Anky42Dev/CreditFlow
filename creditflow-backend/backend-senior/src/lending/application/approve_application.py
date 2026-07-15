from shared.application.outbox import OutboxStore
from shared.application.unit_of_work import UnitOfWork
from shared.application.use_case import UseCase

from ..domain.repositories.application_repository import ApplicationRepository
from ..infrastructure.mappers import ApplicationMapper


class ApproveApplicationUseCase(UseCase):
    """DOC 5 §6.1, Roadmap Этап 2 п.5. Wraps apps.applications.services.approve_application
    (Doc 3 §10) — unchanged — in the shared UnitOfWork; see
    SubmitApplicationUseCase's docstring for why the legacy service, not the
    domain aggregate, still drives the mutation this stage, and for the same
    "replay the transition on a pre-mutation aggregate to get pull_events()"
    strategy used here for the Roadmap Этап 3 п.7 outbox write (ApplicationApproved).

    approve_application also runs disburse_loan inline (Doc 3 §9.1) before
    returning, so by the time this use case regains control `model.status` is
    already DISBURSED, not APPROVED — the pre-mutation aggregate is built
    *before* that call specifically so `aggregate.approve_from_manual_review()`
    still sees MANUAL_REVIEW -> APPROVED and raises the right event regardless
    of what the legacy service did afterwards.
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

    def execute(self, application_id: int, comment: str = "", actor=None, request=None):
        from apps.applications.services import approve_application

        with self.uow:
            model = self.repo.get_model(application_id)
            aggregate = ApplicationMapper.to_domain(model)  # pre-mutation (MANUAL_REVIEW)
            model = approve_application(
                model, comment=comment, actor=actor, request=request
            )
            aggregate.approve_from_manual_review()
            self.outbox.append(
                aggregate.pull_events(),
                aggregate_type="CreditApplication",
                aggregate_id=aggregate.id,
            )
        return model
