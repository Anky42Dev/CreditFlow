from django.db import transaction

from shared.application.unit_of_work import UnitOfWork


class DjangoUnitOfWork(UnitOfWork):
    """DOC 5 §5.3. Django-backed implementation of the shared/application
    UnitOfWork ABC (Этап 1). Wraps `transaction.atomic()`; nests safely (via
    savepoints) inside the `@transaction.atomic` decorators already used by
    apps.lending.services.disburse_loan/repay, so use cases in this stage can
    wrap those legacy calls without changing their own transactional
    behavior.
    """

    def __enter__(self) -> "DjangoUnitOfWork":
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._atomic.__exit__(exc_type, exc_val, exc_tb)
