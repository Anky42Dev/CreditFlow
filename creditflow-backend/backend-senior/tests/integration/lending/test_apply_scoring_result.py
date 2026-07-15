"""DOC 5 §7/§8, Roadmap Этап 4 п.11: ApplyScoringResultUseCase applies a
decision computed externally (by scoring_service) to a SUBMITTED application
— the broker-driven counterpart of ApplyScoringDecisionUseCase, exercised
directly against the real DB, mirroring tests/integration/lending/
test_use_cases.py's style.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.applications.models import CreditApplication, ScoringResult
from apps.lending.models import Loan
from lending.application.apply_scoring_result import ApplyScoringResultUseCase
from lending.infrastructure.repositories import DjangoApplicationRepository
from shared.infrastructure.unit_of_work import DjangoUnitOfWork

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


class TestApplyScoringResultUseCase:
    def test_applies_approved_decision_and_disburses(self, submitted_application):
        use_case = ApplyScoringResultUseCase(DjangoApplicationRepository(), DjangoUnitOfWork())

        result = use_case.execute(
            submitted_application.id, score=820, decision="APPROVED", reason="Sufficient income"
        )

        assert result.status == "DISBURSED"
        assert ScoringResult.objects.filter(
            application=submitted_application, score=820, decision="APPROVED"
        ).exists()
        assert Loan.objects.filter(application=submitted_application).exists()

    def test_applies_manual_review_decision(self, submitted_application):
        use_case = ApplyScoringResultUseCase(DjangoApplicationRepository(), DjangoUnitOfWork())

        result = use_case.execute(
            submitted_application.id, score=600, decision="MANUAL_REVIEW", reason="Borderline"
        )

        assert result.status == "MANUAL_REVIEW"
        assert not Loan.objects.filter(application=submitted_application).exists()

    def test_applies_rejected_decision(self, submitted_application):
        use_case = ApplyScoringResultUseCase(DjangoApplicationRepository(), DjangoUnitOfWork())

        result = use_case.execute(
            submitted_application.id, score=200, decision="REJECTED", reason="High debt-to-income"
        )

        assert result.status == "REJECTED"

    def test_noop_if_already_resolved_by_another_scoring_path(self, submitted_application):
        """Simulates the legacy Celery path (or a duplicate/racing broker
        message) having already scored the application before this
        ScoringCompleted message is applied — must not double-transition or
        create a second ScoringResult (DOC 5 §7 ASSUMPTIONS)."""
        use_case = ApplyScoringResultUseCase(DjangoApplicationRepository(), DjangoUnitOfWork())
        use_case.execute(submitted_application.id, score=820, decision="APPROVED", reason="first")

        result = use_case.execute(submitted_application.id, score=200, decision="REJECTED", reason="second")

        assert result.status == "DISBURSED"
        assert ScoringResult.objects.filter(application=submitted_application).count() == 1
