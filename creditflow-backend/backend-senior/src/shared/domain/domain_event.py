from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DomainEvent:
    """DOC 5 §4.3: base for domain events raised by aggregates and recorded to the
    outbox (Этап 3). `occurred_at` is keyword-only so subclasses can add required
    positional fields without violating dataclass field-ordering rules.
    """

    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), kw_only=True
    )
