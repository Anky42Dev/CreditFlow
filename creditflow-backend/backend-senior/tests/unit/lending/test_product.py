from decimal import Decimal

import pytest

from lending.domain.entities.product import CreditProduct
from lending.domain.value_objects.money import Money
from lending.domain.value_objects.term import Term
from shared.domain.errors import DomainError


def make_product(**overrides):
    defaults = dict(
        id=1,
        min_amount=Money(Decimal("10000")),
        max_amount=Money(Decimal("500000")),
        interest_rate=Decimal("12"),
        min_term_months=3,
        max_term_months=36,
    )
    defaults.update(overrides)
    return CreditProduct(**defaults)


def test_validate_amount_within_bounds_ok():
    make_product().validate_amount(Money(Decimal("100000")))


def test_validate_amount_below_min_rejected():
    with pytest.raises(DomainError):
        make_product().validate_amount(Money(Decimal("1000")))


def test_validate_amount_above_max_rejected():
    with pytest.raises(DomainError):
        make_product().validate_amount(Money(Decimal("1000000")))


def test_validate_term_out_of_bounds_rejected():
    with pytest.raises(DomainError):
        make_product().validate_term(Term(60))


def test_calc_annuity_matches_middle_expected_range():
    # Doc 3 §6.2 / apps.applications.tests.CalcAnnuityTests: 100000 @ 12% for 12 months.
    payment = make_product(interest_rate=Decimal("12")).calc_annuity(
        Money(Decimal("100000")), Term(12)
    )
    assert Decimal("8800") < payment.amount < Decimal("8900")


def test_calc_annuity_zero_rate_splits_evenly():
    payment = make_product(interest_rate=Decimal("0")).calc_annuity(
        Money(Decimal("120000")), Term(12)
    )
    assert payment.amount == Decimal("10000.00")
