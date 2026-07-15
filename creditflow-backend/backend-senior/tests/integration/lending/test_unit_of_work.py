"""DOC 5 §5.3: DjangoUnitOfWork commits on success and rolls back on error."""

from decimal import Decimal

import pytest

from apps.products.models import CreditProduct
from shared.infrastructure.unit_of_work import DjangoUnitOfWork

pytestmark = pytest.mark.django_db


def test_commits_on_success():
    uow = DjangoUnitOfWork()
    with uow:
        CreditProduct.objects.create(
            name="Тест",
            slug="test-uow-commit",
            min_amount=Decimal("1000.00"),
            max_amount=Decimal("2000.00"),
            interest_rate=Decimal("10.00"),
            min_term_months=1,
            max_term_months=6,
        )
    assert CreditProduct.objects.filter(slug="test-uow-commit").exists()


def test_rolls_back_on_exception():
    uow = DjangoUnitOfWork()
    with pytest.raises(ValueError):
        with uow:
            CreditProduct.objects.create(
                name="Тест",
                slug="test-uow-rollback",
                min_amount=Decimal("1000.00"),
                max_amount=Decimal("2000.00"),
                interest_rate=Decimal("10.00"),
                min_term_months=1,
                max_term_months=6,
            )
            raise ValueError("boom")
    assert not CreditProduct.objects.filter(slug="test-uow-rollback").exists()
