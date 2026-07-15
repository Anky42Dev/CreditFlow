from decimal import Decimal

from shared.application.unit_of_work import UnitOfWork
from shared.application.use_case import UseCase

from ..domain.repositories.loan_repository import LoanRepository


class RepayLoanUseCase(UseCase):
    """DOC 5 §6.1, Roadmap Этап 2 п.5. Wraps apps.lending.services.repay
    (Doc 3 §9.2) — unchanged — in the shared UnitOfWork. `repay()` re-fetches
    the loan itself with `select_for_update` and returns the row it actually
    mutated, so this use case must use that return value (not the pre-call
    `loan` reference `self.repo.get` handed it, which stays stale).
    """

    def __init__(self, repo: LoanRepository, uow: UnitOfWork):
        self.repo = repo
        self.uow = uow

    def execute(
        self,
        loan_id: int,
        amount: Decimal,
        idempotency_key: str,
        actor=None,
        request=None,
    ):
        from apps.lending.services import repay

        with self.uow:
            loan = self.repo.get(loan_id)
            loan = repay(loan, amount, idempotency_key, actor=actor, request=request)
        return loan
