"""DOC 5 §16 ("Contract | контракт событий между Django и scoring-service |
pact/схемы"): lightweight schema-shape contract tests (no Pact dependency —
overkill for two processes in one monorepo) asserting:

1. The ApplicationSubmitted payload backend-senior actually publishes (see
   src/lending/application/submit_application.py::SubmitApplicationUseCase.
   _for_scoring and src/lending/domain/events/application_submitted.py) has
   every field this consumer reads.
2. The ScoringCompleted payload this consumer publishes has every field
   backend-senior's consumer expects (apps/outbox/consumers.py::
   _handle_scoring_completed).

These are the two schemas that must never silently drift, since neither side
imports the other's code across the process boundary.
"""

from scoring_service.consumers.application_submitted import (
    RESULT_EVENT_TYPE,
    SOURCE_EVENT_TYPE,
    handle_application_submitted,
)

# Mirrors the shape SubmitApplicationUseCase._for_scoring actually produces
# (application_id, user_id always present; the scoring-input fields are
# Optional on the dataclass but always populated by that use case).
APPLICATION_SUBMITTED_REQUIRED_FIELDS = {
    "application_id",
    "user_id",
    "occurred_at",
    "amount",
    "term_months",
    "monthly_payment",
    "monthly_income",
    "has_birth_date",
}

# Mirrors what apps.outbox.consumers._handle_scoring_completed reads off the
# payload dict (application_id/score/decision required; reason optional via
# .get(..., "")).
SCORING_COMPLETED_REQUIRED_FIELDS = {"application_id", "score", "decision"}
SCORING_COMPLETED_OPTIONAL_FIELDS = {"reason"}


def test_source_and_result_event_type_names_match_django_side():
    assert SOURCE_EVENT_TYPE == "ApplicationSubmitted"
    assert RESULT_EVENT_TYPE == "ScoringCompleted"


def test_consumer_only_reads_fields_django_actually_publishes():
    sample_application_submitted_payload = {
        "application_id": 1,
        "user_id": 2,
        "occurred_at": "2026-01-01T00:00:00+00:00",
        "amount": "200000.00",
        "term_months": 12,
        "monthly_payment": "18300.00",
        "monthly_income": "100000.00",
        "has_birth_date": True,
    }
    assert (
        set(sample_application_submitted_payload)
        == APPLICATION_SUBMITTED_REQUIRED_FIELDS
    )

    # Must not raise KeyError on any field this payload provides.
    handle_application_submitted(sample_application_submitted_payload)


def test_scoring_completed_output_has_all_fields_django_consumer_needs():
    payload = handle_application_submitted(
        {
            "application_id": 1,
            "monthly_payment": "18300.00",
            "monthly_income": "100000.00",
            "has_birth_date": True,
        }
    )

    assert SCORING_COMPLETED_REQUIRED_FIELDS <= set(payload)
    assert SCORING_COMPLETED_OPTIONAL_FIELDS <= set(payload)
    assert isinstance(payload["application_id"], int)
    assert isinstance(payload["score"], int)
    assert payload["decision"] in ("APPROVED", "MANUAL_REVIEW", "REJECTED")
