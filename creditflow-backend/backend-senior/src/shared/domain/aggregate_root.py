from .domain_event import DomainEvent
from .entity import Entity


class AggregateRoot(Entity):
    """DOC 5 §4.2, §4.3: an Entity that also collects DomainEvents raised while
    executing its business methods. Events are pulled (and cleared) by the
    infrastructure layer when persisting, for writing to the outbox (Этап 3).
    """

    def __init__(self, id):
        super().__init__(id)
        self._events: list[DomainEvent] = []

    def raise_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events
