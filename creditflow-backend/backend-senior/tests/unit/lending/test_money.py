from decimal import Decimal

import pytest

from lending.domain.value_objects.money import Money


def test_negative_amount_rejected():
    with pytest.raises(ValueError):
        Money(Decimal("-1"))


def test_add_same_currency():
    total = Money(Decimal("100")) + Money(Decimal("50"))
    assert total == Money(Decimal("150"))


def test_sub_same_currency():
    remainder = Money(Decimal("100")) - Money(Decimal("40"))
    assert remainder == Money(Decimal("60"))


def test_add_mismatched_currency_rejected():
    with pytest.raises(ValueError):
        Money(Decimal("10"), "KGS") + Money(Decimal("10"), "USD")


def test_ordering():
    assert Money(Decimal("10")) <= Money(Decimal("20"))
    assert Money(Decimal("20")) >= Money(Decimal("10"))
