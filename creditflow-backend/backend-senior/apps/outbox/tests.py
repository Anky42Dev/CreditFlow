"""Этап 7 §12.3: trace_id propagation through the outbox
(DjangoOutboxStore.append -> OutboxMessage.trace_id -> relay_outbox_messages
-> broker payload), so scoring_service and apps.outbox.consumers can rebind
the same correlation id the originating HTTP request had.
"""

import pytest
import structlog
from django.utils import timezone

from apps.outbox.models import OutboxMessage
from apps.outbox.tasks import relay_outbox_messages
from shared.domain.domain_event import DomainEvent
from shared.infrastructure.outbox import DjangoOutboxStore

pytestmark = pytest.mark.django_db


def test_append_stamps_trace_id_from_contextvars():
    structlog.contextvars.bind_contextvars(trace_id="trace-123")
    try:
        DjangoOutboxStore().append(
            [DomainEvent()], aggregate_type="Test", aggregate_id=1
        )
    finally:
        structlog.contextvars.clear_contextvars()

    message = OutboxMessage.objects.get()
    assert message.trace_id == "trace-123"


def test_append_leaves_trace_id_null_outside_a_request():
    structlog.contextvars.clear_contextvars()
    DjangoOutboxStore().append([DomainEvent()], aggregate_type="Test", aggregate_id=2)

    message = OutboxMessage.objects.get()
    assert message.trace_id is None


def test_relay_merges_trace_id_into_published_payload(monkeypatch):
    published = []

    class _FakeBus:
        def publish(self, event_type, payload):
            published.append((event_type, payload))

    import shared.infrastructure.event_bus as event_bus_module

    monkeypatch.setattr(event_bus_module, "get_event_bus", lambda: _FakeBus())

    OutboxMessage.objects.create(
        event_type="TestEvent",
        aggregate_type="Test",
        aggregate_id="3",
        payload={"foo": "bar"},
        occurred_at=timezone.now(),
        trace_id="trace-456",
    )

    relay_outbox_messages()

    assert len(published) == 1
    event_type, payload = published[0]
    assert event_type == "TestEvent"
    assert payload == {"foo": "bar", "trace_id": "trace-456"}


def test_consume_once_binds_and_unbinds_trace_id(monkeypatch):
    from apps.outbox import consumers

    captured = {}

    class _FakeBus:
        def consume_one(self, event_type, timeout=1.0):
            return {"trace_id": "trace-789"}

    import shared.infrastructure.event_bus as event_bus_module

    monkeypatch.setattr(event_bus_module, "get_event_bus", lambda: _FakeBus())

    def _handler(payload):
        captured["trace_id_during"] = structlog.contextvars.get_contextvars().get(
            "trace_id"
        )

    monkeypatch.setattr(
        consumers, "get_handlers", lambda: {"ApplicationSubmitted": _handler}
    )

    processed = consumers.consume_once("ApplicationSubmitted", timeout=0.1)

    assert processed is True
    assert captured["trace_id_during"] == "trace-789"
    assert "trace_id" not in structlog.contextvars.get_contextvars()
