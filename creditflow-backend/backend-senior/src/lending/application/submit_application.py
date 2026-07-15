import dataclasses

from shared.application.outbox import OutboxStore
from shared.application.unit_of_work import UnitOfWork
from shared.application.use_case import UseCase
from shared.domain.domain_event import DomainEvent

from ..domain.events.application_submitted import ApplicationSubmitted
from ..domain.repositories.application_repository import ApplicationRepository
from ..infrastructure.mappers import ApplicationMapper


class SubmitApplicationUseCase(UseCase):
    """DOC 5 §6.1, Roadmap Этап 2 п.5. Delegates the transition itself to
    apps.applications.services.submit_application (Doc 3 §6.2) — unchanged, so
    it still owns validation, the annuity calc, and dispatching the async
    scoring task exactly as Middle's tests verify. This use case only adds the
    shared transactional boundary (UnitOfWork) and DI wiring (Этап 1 п.2)
    around that call; see Этап 2 report ASSUMPTIONS for why the domain
    aggregate isn't driving the mutation yet.

    In CELERY_TASK_ALWAYS_EAGER mode `score_application.delay(...)` inside
    submit_application runs synchronously, but perform_scoring fetches its own
    fresh CreditApplication instance rather than mutating the one
    submit_application returns — so `model` can be stale (still "SUBMITTED")
    after an eager scoring cascade that already moved it to APPROVED/REJECTED/
    MANUAL_REVIEW/DISBURSED. The original view called
    `application.refresh_from_db()` for exactly this reason; `refresh_from_db`
    here (same transaction, so it sees the cascade's writes) is that same fix.

    Roadmap Этап 3 п.7 (transactional outbox): since submit_application still
    drives the mutation directly on `model` rather than through
    CreditApplicationAggregate, this use case builds a *second*, independent
    aggregate from the pre-mutation model (`ApplicationMapper.to_domain`) and
    replays the same transition (`aggregate.submit()`) purely to get the
    aggregate's `raise_event`/`pull_events()` plumbing (Этап 1 §4.2/§4.3) to
    produce the ApplicationSubmitted event this stage needs — this is the
    "(a)" strategy flagged in Этап 2's ASSUMPTIONS. Because the legacy service
    already validated the same amount/term bounds with the same Decimal
    arithmetic (apps.applications.services.calc_annuity vs
    CreditProduct.calc_annuity), `aggregate.submit()` is not expected to ever
    raise here in practice; if the two implementations ever drift, this would
    surface as a 500 instead of the legacy service's 400/409 — an accepted,
    narrow coupling rather than a new source of independent failure.

    Roadmap Этап 4 (scoring_service): ApplicationSubmitted is what the
    (external, standalone) FastAPI scoring service consumes to compute a
    decision — but the aggregate only ever raises it with application_id/
    user_id (Lending-context data; the aggregate must not know about
    Identity's Profile). `_for_scoring` enriches the *outbox* copy of the
    event with the scoring inputs (amount/term/monthly_payment from this
    context, monthly_income/has_birth_date from Identity's Profile) at this
    application-layer boundary, where crossing bounded contexts is allowed —
    the domain event raised by the aggregate itself stays minimal.
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
        from apps.applications.services import submit_application
        from common.metrics import applications_submitted_total

        with self.uow:
            model = self.repo.get_model(application_id)
            aggregate = ApplicationMapper.to_domain(model)  # pre-mutation (DRAFT)
            submit_application(model)
            model.refresh_from_db()
            aggregate.submit()
            events = [
                self._for_scoring(event, model) for event in aggregate.pull_events()
            ]
            self.outbox.append(
                events,
                aggregate_type="CreditApplication",
                aggregate_id=aggregate.id,
            )
        applications_submitted_total.inc()  # DOC 5 §12.1
        return model

    @staticmethod
    def _for_scoring(event: DomainEvent, model) -> DomainEvent:
        if not isinstance(event, ApplicationSubmitted):
            return event
        profile = getattr(model.user, "profile", None)
        return dataclasses.replace(
            event,
            amount=model.amount,
            term_months=model.term_months,
            monthly_payment=model.monthly_payment,
            monthly_income=getattr(profile, "monthly_income", None),
            has_birth_date=bool(profile and profile.birth_date),
        )
