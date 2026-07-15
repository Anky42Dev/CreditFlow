from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    """DOC 5 §5.3: transactional boundary a use case runs inside. The Django-backed
    implementation (wrapping `transaction.atomic()`) is added in Этап 2 alongside
    the repository implementations it coordinates.
    """

    @abstractmethod
    def __enter__(self) -> "UnitOfWork": ...

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
