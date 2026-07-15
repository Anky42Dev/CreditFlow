import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from common.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

RELAY_BATCH_SIZE = 100


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def relay_outbox_messages(self) -> int:
    """DOC 5 §8.1, Roadmap Этап 3 п.7: the Outbox Relay. Scheduled every 5s via
    Celery Beat (config.settings.CELERY_BEAT_SCHEDULE). Reads unpublished rows
    (oldest first), publishes each to its event-type queue on the broker
    (`shared.infrastructure.event_bus`), and flips `published`/`published_at`
    — one row at a time, so a mid-batch publish failure only leaves later rows
    unpublished (picked up by the next tick) rather than losing the whole batch.

    `select_for_update(skip_locked=True)` lets multiple relay workers run
    concurrently without double-publishing the same row.
    """
    from shared.infrastructure.event_bus import get_event_bus

    from .models import OutboxMessage

    bus = get_event_bus()
    published = 0
    with transaction.atomic():
        messages = list(
            OutboxMessage.objects.select_for_update(skip_locked=True)
            .filter(published=False)
            .order_by("created_at")[:RELAY_BATCH_SIZE]
        )
        for message in messages:
            # DOC 5 §12.3: threads trace_id into the broker payload (not a
            # separate column) so scoring_service — which has no visibility
            # into OutboxMessage — can read it back out like any other
            # payload field.
            payload = {**message.payload, "trace_id": message.trace_id}
            with tracer.start_as_current_span(
                "outbox.publish",
                attributes={
                    "event_type": message.event_type,
                    "aggregate_id": message.aggregate_id,
                    "app.trace_id": message.trace_id or "",
                },
            ):
                try:
                    bus.publish(message.event_type, payload)
                except Exception:
                    logger.exception(
                        "relay_outbox_messages: failed to publish outbox id=%s type=%s",
                        message.id,
                        message.event_type,
                    )
                    continue
            message.published = True
            message.published_at = timezone.now()
            message.save(update_fields=["published", "published_at"])
            published += 1
    return published
