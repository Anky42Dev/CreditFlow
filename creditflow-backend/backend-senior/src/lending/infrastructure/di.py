"""DOC 5 §6.2, Roadmap Этап 2 п.5, Этап 3 п.7-9, Этап 4 п.11. Bounded-context DI
container wiring the lending use cases (Submit/Approve/Reject/Repay/
ApplyScoringDecision/ApplyScoringResult) and the loan-issuance saga to their
repository/UnitOfWork/OutboxStore
dependencies via the shared/infrastructure/di.py primitives built in Этап 1.

`container` is a module-level singleton instance, imported by presentation-layer
views (apps/applications/views.py, apps/adminpanel/views.py, apps/lending/views.py),
the Celery task apps/applications/tasks.py::score_application (Этап 3), and the
broker consumer apps/outbox/consumers.py (Этап 3) — none of these call
apps.*.services, the ORM, or the broker directly.
"""

from shared.infrastructure.di import Container, Factory
from shared.infrastructure.outbox import DjangoOutboxStore
from shared.infrastructure.unit_of_work import DjangoUnitOfWork

from ..application.apply_scoring_decision import ApplyScoringDecisionUseCase
from ..application.apply_scoring_result import ApplyScoringResultUseCase
from ..application.approve_application import ApproveApplicationUseCase
from ..application.reject_application import RejectApplicationUseCase
from ..application.repay_loan import RepayLoanUseCase
from ..application.sagas.loan_issuance_saga import LoanIssuanceSaga
from ..application.submit_application import SubmitApplicationUseCase
from .repositories import DjangoApplicationRepository, DjangoLoanRepository


class LendingContainer(Container):
    application_repo = Factory(DjangoApplicationRepository)
    loan_repo = Factory(DjangoLoanRepository)
    uow = Factory(DjangoUnitOfWork)
    outbox = Factory(DjangoOutboxStore)

    submit_application = Factory(
        SubmitApplicationUseCase, repo=application_repo, uow=uow, outbox=outbox
    )
    approve_application = Factory(
        ApproveApplicationUseCase, repo=application_repo, uow=uow, outbox=outbox
    )
    reject_application = Factory(
        RejectApplicationUseCase, repo=application_repo, uow=uow, outbox=outbox
    )
    repay_loan = Factory(RepayLoanUseCase, repo=loan_repo, uow=uow)
    apply_scoring_decision = Factory(
        ApplyScoringDecisionUseCase, repo=application_repo, uow=uow, outbox=outbox
    )
    apply_scoring_result = Factory(
        ApplyScoringResultUseCase, repo=application_repo, uow=uow, outbox=outbox
    )
    loan_issuance_saga = Factory(LoanIssuanceSaga, uow=uow)


container = LendingContainer()
