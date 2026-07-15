"""DOC 5 §7, Roadmap Этап 4 п.10-11: SubmitApplicationUseCase enriches the
ApplicationSubmitted outbox payload with the scoring inputs the external
scoring_service consumer needs (amount/term/monthly_payment from Lending,
monthly_income/has_birth_date from Identity's Profile) — see
lending.application.submit_application.SubmitApplicationUseCase._for_scoring.

Mocks apps.applications.tasks.score_application.delay, matching the existing
pattern in apps/applications/tests.py::
test_submit_does_not_score_synchronously_without_eager_mode — avoids a real
Celery broker connection and isolates the assertion to the outbox payload.
"""

from decimal import Decimal
from unittest import mock

import pytest

from apps.applications.models import CreditApplication
from apps.outbox.models import OutboxMessage
from lending.application.submit_application import SubmitApplicationUseCase
from lending.infrastructure.repositories import DjangoApplicationRepository
from shared.infrastructure.unit_of_work import DjangoUnitOfWork

pytestmark = pytest.mark.django_db


def test_submit_enriches_outbox_payload_with_scoring_inputs(product, user):
    application = CreditApplication.objects.create(
        user=user, product=product, amount=Decimal("200000.00"), term_months=12
    )
    use_case = SubmitApplicationUseCase(DjangoApplicationRepository(), DjangoUnitOfWork())

    with mock.patch("apps.applications.tasks.score_application.delay"):
        use_case.execute(application.id)

    message = OutboxMessage.objects.get(
        event_type="ApplicationSubmitted", aggregate_id=str(application.id)
    )
    payload = message.payload
    assert Decimal(payload["amount"]) == Decimal("200000.00")
    assert payload["term_months"] == 12
    assert payload["monthly_payment"] is not None
    assert payload["monthly_income"] == "100000.00"  # from the `user` fixture's profile
    assert payload["has_birth_date"] is True


def test_submit_enriches_with_none_income_when_profile_missing_data(product, underwriter_user):
    """underwriter_user (conftest.py) has no monthly_income/birth_date set —
    the enrichment must degrade to None/False, not raise."""
    application = CreditApplication.objects.create(
        user=underwriter_user, product=product, amount=Decimal("50000.00"), term_months=6
    )
    use_case = SubmitApplicationUseCase(DjangoApplicationRepository(), DjangoUnitOfWork())

    with mock.patch("apps.applications.tasks.score_application.delay"):
        use_case.execute(application.id)

    message = OutboxMessage.objects.get(
        event_type="ApplicationSubmitted", aggregate_id=str(application.id)
    )
    assert message.payload["monthly_income"] is None
    assert message.payload["has_birth_date"] is False
