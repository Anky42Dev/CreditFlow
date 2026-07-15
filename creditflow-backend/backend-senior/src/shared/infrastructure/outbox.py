import dataclasses

import structlog

from shared.application.outbox import OutboxStore
from shared.domain.domain_event import DomainEvent


def serialize_event(event: DomainEvent) -> dict:
    """Recursively unpacks the event dataclass (and any nested VO dataclasses,
    e.g. Money) into a plain dict. Decimal/datetime values inside are handled
    at write time by OutboxMessage.payload's DjangoJSONEncoder, not here.
    """
    return dataclasses.asdict(event)


class DjangoOutboxStore(OutboxStore):
    """DOC 5 §5.2/§8.1, Roadmap Этап 3 п.7. Writes one OutboxMessage row per
    event, using the caller's ambient transaction (the use case's
    `with self.uow:` block) — this class opens no transaction of its own.
    """

    def append(
        self, events: list[DomainEvent], *, aggregate_type: str, aggregate_id
    ) -> None:
        from apps.outbox.models import OutboxMessage

        # DOC 5 §12.3: bound by common.middleware.RequestContextMiddleware
        # for HTTP-triggered writes; absent (None) for system-initiated ones
        # (Celery Beat, management commands) — see OutboxMessage.trace_id.
        trace_id = structlog.contextvars.get_contextvars().get("trace_id")

        for event in events:
            OutboxMessage.objects.create(
                event_type=type(event).__name__,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id),
                payload=serialize_event(event),
                occurred_at=event.occurred_at,
                trace_id=trace_id,
            )
