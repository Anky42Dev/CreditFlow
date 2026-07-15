from abc import ABC, abstractmethod
from typing import Any


class LoanRepository(ABC):
    """DOC 5 §5.1. Этап 1 modelled only CreditProduct/CreditApplicationAggregate
    in the domain layer; Loan (Payments concerns per DOC 5 §2.2) has no domain
    aggregate yet and building one is out of scope for Этап 2 пп.4-6. `get`
    therefore returns the persisted record itself — RepayLoanUseCase hands it
    straight to apps.lending.services.repay(), which only reads its `.id`
    before re-fetching with `select_for_update` (see that function's
    docstring), so no domain type is needed here for this stage.
    """

    @abstractmethod
    def get(self, loan_id: int) -> Any: ...

    @abstractmethod
    def save(self, loan: Any) -> None: ...
