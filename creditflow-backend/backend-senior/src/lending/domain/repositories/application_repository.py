from abc import ABC, abstractmethod
from typing import Any

from ..entities.application import CreditApplicationAggregate


class ApplicationRepository(ABC):
    """DOC 5 §5.1. `get` / `save` are the domain-facing contract: `get` maps the
    persisted record to a `CreditApplicationAggregate` (via
    infrastructure/mappers.py) and `save` writes an aggregate's mutable fields
    back. `get_model` is a pragmatic bridge kept only for Этап 2: it hands back
    the underlying persisted record itself so this stage's use cases can
    delegate the actual transition to the still-untouched
    apps.applications.services functions (submit_application,
    approve_application, reject_application), which mutate that record
    directly and own the audit/notification/scoring side effects already
    covered by Middle's tests. Driving those transitions through the aggregate
    end-to-end (retiring `get_model`) is follow-up work, not this stage's job.
    """

    @abstractmethod
    def get(self, application_id: int) -> CreditApplicationAggregate: ...

    @abstractmethod
    def get_model(self, application_id: int) -> Any: ...

    @abstractmethod
    def save(self, aggregate: CreditApplicationAggregate) -> None: ...
