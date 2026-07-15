"""DOC 5 §7.1, Roadmap Этап 4 п.11: consumes ApplicationSubmitted (published
to the broker by backend-senior's SubmitApplicationUseCase, enriched with
scoring inputs — see src/lending/application/submit_application.py
_for_scoring), computes a decision via the local ScoringEngine, and
publishes ScoringCompleted for backend-senior's ScoringCompleted consumer
(apps.outbox.consumers._handle_scoring_completed) to apply.

Run as its own long-lived process, independent of the FastAPI HTTP app
(DOC 5 §7.1: async/CPU-bound work, its own scaling), e.g.:
    python -m scoring_service.consumers.application_submitted
"""

import logging
from decimal import Decimal

from ..domain.scoring import ScoringEngine, ScoringInput
from ..event_bus import get_event_bus

logger = logging.getLogger(__name__)

SOURCE_EVENT_TYPE = "ApplicationSubmitted"
RESULT_EVENT_TYPE = "ScoringCompleted"


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def handle_application_submitted(payload: dict) -> dict:
    """Pure transform: ApplicationSubmitted payload -> ScoringCompleted
    payload. Kept side-effect-free (no publish here) so it's unit-testable
    without a broker — see scoring_service/tests/unit/test_consumer.py."""
    scoring_input = ScoringInput(
        application_id=payload["application_id"],
        monthly_payment=_to_decimal(payload.get("monthly_payment")) or Decimal("0"),
        monthly_income=_to_decimal(payload.get("monthly_income")),
        has_birth_date=bool(payload.get("has_birth_date")),
    )
    result = ScoringEngine.evaluate(scoring_input)
    return {
        "application_id": result.application_id,
        "score": result.score,
        "decision": result.decision,
        "reason": result.reason,
        # DOC 5 §12.3: carries the correlation id backend-senior threaded
        # into ApplicationSubmitted (see apps.outbox.tasks.relay_outbox_messages)
        # back into ScoringCompleted, so apps.outbox.consumers can rebind it
        # when applying this decision.
        "trace_id": payload.get("trace_id"),
    }


def consume_once(timeout: float = 1.0) -> bool:
    """Pulls and processes a single ApplicationSubmitted message, if any is
    available within `timeout` seconds. Returns True if one was processed."""
    bus = get_event_bus()
    payload = bus.consume_one(SOURCE_EVENT_TYPE, timeout=timeout)
    if payload is None:
        return False
    result_payload = handle_application_submitted(payload)
    bus.publish(RESULT_EVENT_TYPE, result_payload)
    return True


def run_forever(poll_timeout: float = 1.0) -> None:
    logger.info("scoring_service consumer: listening on %s", SOURCE_EVENT_TYPE)
    while True:
        consume_once(timeout=poll_timeout)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
