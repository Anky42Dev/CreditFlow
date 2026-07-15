from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")


class UseCase(ABC, Generic[TRequest, TResponse]):
    """DOC 5 §6.1: application-layer scenario (SubmitApplication, ApproveApplication, ...).

    Concrete use cases are wired in Этап 2 — this base only fixes the shape so
    the DI container (shared/infrastructure/di.py) can provide them uniformly.
    """

    @abstractmethod
    def execute(self, request: TRequest) -> TResponse: ...
