"""DOC 5 §8, Roadmap Этап 4 п.11: the Django-side handler dispatched by
apps.outbox.consumers.get_handlers()["ScoringCompleted"] when the broker
consumer (apps.outbox.management.commands.consume_events) drains a
ScoringCompleted message published by scoring_service.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.applications.models import CreditApplication
from apps.outbox.consumers import EVENT_TYPES, get_handlers

pytestmark = pytest.mark.django_db


@pytest.fixture
def submitted_application(product, user):
    return CreditApplication.objects.create(
        user=user,
        product=product,
        amount=Decimal("200000.00"),
        term_months=12,
        monthly_payment=Decimal("18300.00"),
        status="SUBMITTED",
        submitted_at=timezone.now(),
    )


def test_scoring_completed_is_a_registered_event_type():
    assert "ScoringCompleted" in EVENT_TYPES


def test_scoring_completed_handler_applies_decision(submitted_application):
    handler = get_handlers()["ScoringCompleted"]

    handler(
        {
            "application_id": submitted_application.id,
            "score": 820,
            "decision": "APPROVED",
            "reason": "Sufficient income",
        }
    )

    submitted_application.refresh_from_db()
    assert submitted_application.status == "DISBURSED"


def test_scoring_completed_handler_defaults_missing_reason(submitted_application):
    handler = get_handlers()["ScoringCompleted"]

    handler({"application_id": submitted_application.id, "score": 200, "decision": "REJECTED"})

    submitted_application.refresh_from_db()
    assert submitted_application.status == "REJECTED"
