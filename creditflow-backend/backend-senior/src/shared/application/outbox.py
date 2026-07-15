from abc import ABC, abstractmethod

from shared.domain.domain_event import DomainEvent


class OutboxStore(ABC):
    """DOC 5 §5.1/§8.1, Roadmap Этап 3 п.7: application-layer port for the
    transactional outbox. `append` must be called from inside the same
    UnitOfWork transaction as the aggregate mutation that raised `events`, so
    the DB write and the outbox row commit or roll back together — that
    atomicity, not any property of the broker, is what makes the outbox
    pattern's delivery guarantee hold.
    """

    @abstractmethod
    def append(
        self, events: list[DomainEvent], *, aggregate_type: str, aggregate_id
    ) -> None: ...
