"""DOC 5 §6.1, Roadmap Этап 2 п.5: use cases exercised directly (not via HTTP),
wired to the real Django repositories/UnitOfWork. The HTTP-level regression
coverage for these same flows (audit log, notifications, scoring dispatch,
disbursement) already lives in apps/applications/tests*.py, apps/adminpanel/
tests.py and apps/lending/tests.py — those exercise the same use cases via
the views changed in Этап 2 п.6 and must keep passing unmodified.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.applications.models import CreditApplication
from apps.lending.models import Loan
from common.exceptions import ConflictError
from lending.application.approve_application import ApproveApplicationUseCase
from lending.application.reject_application import RejectApplicationUseCase
from lending.application.repay_loan import RepayLoanUseCase
from lending.application.submit_application import SubmitApplicationUseCase
from lending.infrastructure.repositories import (
    DjangoApplicationRepository,
    DjangoLoanRepository,
)
from shared.infrastructure.unit_of_work import DjangoUnitOfWork

pytestmark = pytest.mark.django_db


@pytest.fixture
def draft_application(product, user):
    return CreditApplication.objects.create(
        user=user, product=product, amount=Decimal("200000.00"), term_months=12
    )


@pytest.fixture
def manual_review_application(product, user):
    application = CreditApplication.objects.create(
        user=user,
        product=product,
        amount=Decimal("200000.00"),
        term_months=12,
        monthly_payment=Decimal("18300.00"),
        status="MANUAL_REVIEW",
        submitted_at=timezone.now(),
    )
    return application


@pytest.fixture
def active_loan(product, user, draft_application):
    return Loan.objects.create(
        application=draft_application,
        user=user,
        principal=Decimal("200000.00"),
        interest_rate=product.interest_rate,
        term_months=12,
        monthly_payment=Decimal("18300.00"),
        outstanding_balance=Decimal("200000.00"),
        status="ACTIVE",
        disbursed_at=timezone.now(),
    )


class TestSubmitApplicationUseCase:
    def test_execute_transitions_to_submitted(self, draft_application, celery_eager):
        use_case = SubmitApplicationUseCase(
            DjangoApplicationRepository(), DjangoUnitOfWork()
        )

        result = use_case.execute(draft_application.id)

        assert result.status in (
            "SUBMITTED",
            "SCORING",
            "APPROVED",
            "REJECTED",
            "MANUAL_REVIEW",
            "DISBURSED",
        )
        draft_application.refresh_from_db()
        assert draft_application.status != "DRAFT"
        assert draft_application.monthly_payment is not None

    def test_execute_non_draft_raises_conflict(self, draft_application, celery_eager):
        use_case = SubmitApplicationUseCase(
            DjangoApplicationRepository(), DjangoUnitOfWork()
        )
        use_case.execute(draft_application.id)

        with pytest.raises(ConflictError):
            use_case.execute(draft_application.id)


class TestApproveApplicationUseCase:
    def test_execute_approves_manual_review_application(
        self, manual_review_application, admin_user
    ):
        use_case = ApproveApplicationUseCase(
            DjangoApplicationRepository(), DjangoUnitOfWork()
        )

        result = use_case.execute(
            manual_review_application.id, comment="ok", actor=admin_user, request=None
        )

        assert result.status == "DISBURSED"
        assert Loan.objects.filter(application=manual_review_application).exists()

    def test_execute_non_manual_review_raises_conflict(
        self, draft_application, admin_user
    ):
        use_case = ApproveApplicationUseCase(
            DjangoApplicationRepository(), DjangoUnitOfWork()
        )

        with pytest.raises(ConflictError):
            use_case.execute(
                draft_application.id, comment="", actor=admin_user, request=None
            )


class TestRejectApplicationUseCase:
    def test_execute_rejects_manual_review_application(
        self, manual_review_application, underwriter_user
    ):
        use_case = RejectApplicationUseCase(
            DjangoApplicationRepository(), DjangoUnitOfWork()
        )

        result = use_case.execute(
            manual_review_application.id,
            reason="risky",
            actor=underwriter_user,
            request=None,
        )

        assert result.status == "REJECTED"

    def test_execute_non_manual_review_raises_conflict(
        self, draft_application, underwriter_user
    ):
        use_case = RejectApplicationUseCase(
            DjangoApplicationRepository(), DjangoUnitOfWork()
        )

        with pytest.raises(ConflictError):
            use_case.execute(
                draft_application.id, reason="", actor=underwriter_user, request=None
            )


class TestRepayLoanUseCase:
    def test_execute_reduces_outstanding_balance(self, active_loan, user):
        use_case = RepayLoanUseCase(DjangoLoanRepository(), DjangoUnitOfWork())

        result = use_case.execute(
            active_loan.id,
            Decimal("18300.00"),
            idempotency_key="repay-key-1",
            actor=user,
            request=None,
        )

        assert result.outstanding_balance == Decimal("181700.00")
        active_loan.refresh_from_db()
        assert active_loan.outstanding_balance == Decimal("181700.00")

    def test_execute_duplicate_idempotency_key_raises_conflict(self, active_loan, user):
        use_case = RepayLoanUseCase(DjangoLoanRepository(), DjangoUnitOfWork())
        use_case.execute(
            active_loan.id,
            Decimal("18300.00"),
            idempotency_key="repay-key-2",
            actor=user,
            request=None,
        )

        with pytest.raises(ConflictError):
            use_case.execute(
                active_loan.id,
                Decimal("18300.00"),
                idempotency_key="repay-key-2",
                actor=user,
                request=None,
            )
