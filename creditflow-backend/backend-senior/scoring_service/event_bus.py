"""DOC 5 §7/§8: standalone kombu-based event bus for scoring_service.

Deliberately duplicates shared.infrastructure.event_bus.KombuEventBus's
wire protocol (one SimpleQueue per event type, JSON-serialized) rather than
importing it — that module lives inside the Django project's src/ tree and
this service must be importable/deployable without Django installed (DOC 5
§7.1). Both sides must agree on EVENT_BROKER_URL and queue-per-event-type
naming to interoperate; there's no other shared code between them.
"""

import queue
from abc import ABC, abstractmethod

from kombu import Connection


class EventBus(ABC):
    @abstractmethod
    def publish(self, event_type: str, payload: dict) -> None: ...

    @abstractmethod
    def consume_one(self, event_type: str, timeout: float = 1.0) -> dict | None: ...


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
    """Reads EVENT_BROKER_URL at call time (not import time) so tests can
    monkeypatch config.EVENT_BROKER_URL per-test."""
    from . import config

    return KombuEventBus(config.EVENT_BROKER_URL)
