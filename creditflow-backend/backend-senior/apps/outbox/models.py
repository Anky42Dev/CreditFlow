from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class OutboxMessage(models.Model):
    """DOC 5 §5.1/§8.1, Roadmap Этап 3 п.7: a domain event recorded in the same
    DB transaction as the aggregate mutation that raised it (see
    `shared.infrastructure.outbox.DjangoOutboxStore.append`, called from the
    lending use cases in `src/lending/application/`). The Outbox Relay
    (`apps.outbox.tasks.relay_outbox_messages`, scheduled every 5s via Celery
    Beat) publishes unpublished rows to the broker and flips `published`.

    `payload` is the event's own field set (dataclasses.asdict), so a consumer
    never needs to join back to `occurred_at`/`aggregate_id` columns — those
    are duplicated onto dedicated columns purely so the relay/DB can filter
    and order without deserializing JSON.
    """

    event_type = models.CharField(max_length=100, db_index=True)
    aggregate_type = models.CharField(max_length=100)
    aggregate_id = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(encoder=DjangoJSONEncoder)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    # DOC 5 §12.3: the correlation id bound by
    # common.middleware.RequestContextMiddleware for the request that raised
    # this event (shared.infrastructure.outbox.DjangoOutboxStore.append
    # reads it from structlog's contextvars). Nullable — system-initiated
    # events (Celery Beat, management commands) have no request to inherit
    # one from. The Outbox Relay (apps.outbox.tasks) merges it into the
    # published payload so it threads through the broker into
    # scoring_service and back (apps.outbox.consumers).
    trace_id = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "outbox_messages"
        indexes = [
            # Roadmap Этап 3 п.7: the Relay's poll query (unpublished, oldest first).
            models.Index(fields=["published", "created_at"]),
        ]

    def __str__(self):
        return f"Outbox<{self.id}> {self.event_type} published={self.published}"
