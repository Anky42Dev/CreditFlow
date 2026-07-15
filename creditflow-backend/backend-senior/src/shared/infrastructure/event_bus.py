"""DOC 5 §3 (`shared/infrastructure/event_bus.py`), §8. Roadmap Этап 3 п.8: the
broker abstraction domain events are published to (by the Outbox Relay,
apps.outbox.tasks.relay_outbox_messages) and consumed from (by
apps.outbox.consumers, e.g. the loan-issuance saga).

Built on `kombu` (already installed transitively via `celery`) rather than a
raw `pika` client: kombu is transport-agnostic, so the exact same
`KombuEventBus` code talks to a real RabbitMQ (`amqp://...`) in
docker-compose/production and to kombu's in-memory transport (`memory://`) in
tests and default local dev, with zero test-only branching in this module.
One queue per event type (`ApplicationSubmitted`, `ApplicationApproved`,
`ApplicationRejected`) via kombu's `SimpleQueue` — a routing exchange isn't
needed yet since each event type currently has at most one consumer group.
"""

import queue
from abc import ABC, abstractmethod

from django.conf import settings
from kombu import Connection


class EventBus(ABC):
    @abstractmethod
    def publish(self, event_type: str, payload: dict) -> None: ...

    @abstractmethod
    def consume_one(self, event_type: str, timeout: float = 1.0) -> dict | None:
        """Blocks up to `timeout` seconds for one message on `event_type`'s
        queue; acks and returns its payload, or returns None on timeout."""


class KombuEventBus(EventBus):
    def __init__(self, broker_url: str):
        self.broker_url = broker_url

    def publish(self, event_type: str, payload: dict) -> None:
        with Connection(self.broker_url) as connection:
            simple_queue = connection.SimpleQueue(event_type)
            try:
                simple_queue.put(payload, serializer="json")
            finally:
                simple_queue.close()

    def consume_one(self, event_type: str, timeout: float = 1.0) -> dict | None:
        with Connection(self.broker_url) as connection:
            simple_queue = connection.SimpleQueue(event_type)
            try:
                message = simple_queue.get(block=True, timeout=timeout)
            except queue.Empty:
                return None
            finally:
                simple_queue.close()
            payload = message.payload
            message.ack()
            return payload


def get_event_bus() -> EventBus:
    """Reads settings.EVENT_BROKER_URL at call time (not import time) so the
    `settings` pytest fixture can override it per-test."""
    return KombuEventBus(getattr(settings, "EVENT_BROKER_URL", "memory://"))
