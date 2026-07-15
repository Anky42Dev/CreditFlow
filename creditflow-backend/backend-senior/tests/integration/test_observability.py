"""Этап 7 §12.1: Prometheus counters/histograms actually observe at the
call sites they're wired into — submit_application, ScoringCompleted
application, loan disbursement.
"""

from decimal import Decimal
from unittest import mock

import pytest

from apps.applications.models import CreditApplication
from apps.applications.services import calc_annuity
from apps.outbox.consumers import get_handlers
from common.metrics import (
    applications_submitted_total,
    loans_disbursed_amount_total,
    scoring_duration_seconds,
)
from lending.application.submit_application import SubmitApplicationUseCase
from lending.infrastructure.repositories import DjangoApplicationRepository
from shared.infrastructure.unit_of_work import DjangoUnitOfWork

pytestmark = pytest.mark.django_db


def _histogram_count(histogram) -> float:
    """prometheus_client's Histogram has no public '.count' accessor; the
    _count sample is exposed through collect(), the documented introspection
    API, rather than a private attribute."""
    for metric in histogram.collect():
        for sample in metric.samples:
            if sample.name.endswith("_count"):
                return sample.value
    return 0.0


def test_submit_application_increments_applications_submitted_total(product, user):
    application = CreditApplication.objects.create(
        user=user, product=product, amount=Decimal("200000.00"), term_months=12
    )
    use_case = SubmitApplicationUseCase(
        DjangoApplicationRepository(), DjangoUnitOfWork()
    )
    before = applications_submitted_total._value.get()

    with mock.patch("apps.applications.tasks.score_application.delay"):
        use_case.execute(application.id)

    assert applications_submitted_total._value.get() == before + 1


def test_apply_scoring_result_observes_scoring_duration(product, user):
    from django.utils import timezone

    application = CreditApplication.objects.create(
        user=user,
        product=product,
        amount=Decimal("200000.00"),
        term_months=12,
        monthly_payment=Decimal("18300.00"),
        status="SUBMITTED",
        submitted_at=timezone.now(),
    )
    before_count = _histogram_count(scoring_duration_seconds)

    get_handlers()["ScoringCompleted"](
        {
            "application_id": application.id,
            "score": 820,
            "decision": "APPROVED",
            "reason": "Sufficient income",
        }
    )

    assert _histogram_count(scoring_duration_seconds) == before_count + 1


def test_disbursement_increments_loans_disbursed_amount_total(product, user):
    from apps.lending.services import disburse_loan

    amount = Decimal("200000.00")
    application = CreditApplication.objects.create(
        user=user, product=product, amount=amount, term_months=12
    )
    application.monthly_payment = calc_annuity(amount, product.interest_rate, 12)
    application.save()
    before = loans_disbursed_amount_total._value.get()

    disburse_loan(application)

    assert loans_disbursed_amount_total._value.get() == before + float(amount)
