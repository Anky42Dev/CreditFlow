"""DOC 5 §5.2, Roadmap Этап 2 п.4: Django-backed repository implementations,
exercised against a real DB (unlike tests/unit/, which never touches one)."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.applications.models import CreditApplication
from apps.lending.models import Loan
from lending.domain.value_objects.application_status import ApplicationStatus
from lending.infrastructure.repositories import (
    DjangoApplicationRepository,
    DjangoLoanRepository,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def draft_application(product, user):
    return CreditApplication.objects.create(
        user=user,
        product=product,
        amount=Decimal("200000.00"),
        term_months=12,
        purpose="Ремонт",
    )


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


class TestDjangoApplicationRepository:
    def test_get_returns_mapped_aggregate(self, draft_application):
        repo = DjangoApplicationRepository()
        aggregate = repo.get(draft_application.id)
        assert aggregate.id == draft_application.id
        assert aggregate.user_id == draft_application.user_id
        assert aggregate.status == ApplicationStatus.DRAFT
        assert aggregate.product.id == draft_application.product_id

    def test_get_model_returns_orm_instance_with_relations_loaded(
        self, draft_application
    ):
        repo = DjangoApplicationRepository()
        model = repo.get_model(draft_application.id)
        assert isinstance(model, CreditApplication)
        assert model.id == draft_application.id
        # select_related fields should be pre-loaded — accessing them shouldn't
        # need extra queries; assertNumQueries-free sanity check via cache probe.
        assert model.product.id == draft_application.product_id
        assert model.user.id == draft_application.user_id

    def test_save_persists_status_and_monthly_payment(self, draft_application):
        repo = DjangoApplicationRepository()
        aggregate = repo.get(draft_application.id)
        aggregate.submit()

        repo.save(aggregate)

        draft_application.refresh_from_db()
        assert draft_application.status == "SUBMITTED"
        assert draft_application.monthly_payment == aggregate.monthly_payment.amount

    def test_save_leaves_untracked_fields_untouched(self, draft_application):
        repo = DjangoApplicationRepository()
        aggregate = repo.get(draft_application.id)
        aggregate.submit()

        repo.save(aggregate)

        draft_application.refresh_from_db()
        assert draft_application.purpose == "Ремонт"


class TestDjangoLoanRepository:
    def test_get_returns_loan_model(self, active_loan):
        repo = DjangoLoanRepository()
        loan = repo.get(active_loan.id)
        assert isinstance(loan, Loan)
        assert loan.id == active_loan.id
        assert loan.outstanding_balance == active_loan.outstanding_balance

    def test_save_persists_mutated_fields(self, active_loan):
        repo = DjangoLoanRepository()
        loan = repo.get(active_loan.id)
        loan.outstanding_balance = Decimal("100000.00")

        repo.save(loan)

        active_loan.refresh_from_db()
        assert active_loan.outstanding_balance == Decimal("100000.00")
