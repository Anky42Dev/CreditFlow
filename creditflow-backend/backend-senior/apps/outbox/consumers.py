import logging

import structlog

from common.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Roadmap Этап 3 п.8, Этап 4 п.11: domain/integration events consumed from the
# broker. ScoringCompleted is published by the *external* scoring_service
# (DOC 5 §7), not by this codebase — Django only consumes it.
EVENT_TYPES = (
    "ApplicationSubmitted",
    "ApplicationApproved",
    "ApplicationRejected",
    "ScoringCompleted",
)


def _handle_application_approved(payload: dict) -> None:
    """Roadmap Этап 3 п.9: dispatches to the loan-issuance saga."""
    from lending.infrastructure.di import container

    container.loan_issuance_saga().handle(payload)


def _handle_scoring_completed(payload: dict) -> None:
    """Roadmap Этап 4 п.11: applies a decision computed by scoring_service
    (see scoring_service/consumers/application_submitted.py) to the
    application via ApplyScoringResultUseCase. `reason` defaults to "" —
    scoring_service always sends it, but a missing/older payload shouldn't
    crash the consumer over an audit-trail nicety."""
    from lending.infrastructure.di import container

    container.apply_scoring_result().execute(
        application_id=payload["application_id"],
        score=payload["score"],
        decision=payload["decision"],
        reason=payload.get("reason", ""),
    )


def _log_only_handler(event_type: str):
    """ApplicationSubmitted/ApplicationRejected have no Этап 3 consumer of
    their own yet on the Django side (ApplicationSubmitted is consumed by
    scoring_service, an independent process outside this codebase;
    ApplicationRejected has no downstream reaction defined by the roadmap).
    Logging proves the publish -> consume round-trip works end to end
    without inventing unspecified business logic."""

    def _handler(payload: dict) -> None:
        logger.info("consumed %s: %s", event_type, payload)

    return _handler


def get_handlers() -> dict:
    return {
        "ApplicationSubmitted": _log_only_handler("ApplicationSubmitted"),
        "ApplicationApproved": _handle_application_approved,
        "ApplicationRejected": _log_only_handler("ApplicationRejected"),
        "ScoringCompleted": _handle_scoring_completed,
    }


def consume_once(event_type: str, timeout: float = 1.0) -> bool:
    """Pulls and dispatches a single message from `event_type`'s queue, if
    any is available within `timeout` seconds. Returns True if a message was
    processed, False on timeout (queue empty).

    DOC 5 §12.2/§12.3: rebinds the trace_id the Outbox Relay threaded into
    the payload (apps.outbox.tasks.relay_outbox_messages) back into
    structlog's contextvars, so log lines emitted while handling this
    message — including ScoringCompleted messages coming back from the
    external scoring_service — carry the same trace_id the original HTTP
    request did. Also wraps dispatch in a span, since this loop runs outside
    any request Django's auto-instrumentation would otherwise see.
    """
    from shared.infrastructure.event_bus import get_event_bus

    bus = get_event_bus()
    payload = bus.consume_one(event_type, timeout=timeout)
    if payload is None:
        return False

    trace_id = payload.get("trace_id")
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    try:
        with tracer.start_as_current_span(
            "outbox.consume",
            attributes={"event_type": event_type, "app.trace_id": trace_id or ""},
        ):
            get_handlers()[event_type](payload)
    finally:
        structlog.contextvars.unbind_contextvars("trace_id")
    return True


def run_forever(poll_timeout: float = 1.0) -> None:
    """Blocking consumer loop: round-robins the three event queues. Run via
    `python manage.py consume_events` (apps/outbox/management/commands/)."""
    logger.info("consume_events: listening on %s", EVENT_TYPES)
    while True:
        for event_type in EVENT_TYPES:
            consume_once(event_type, timeout=poll_timeout)
