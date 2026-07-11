from decimal import Decimal

from apps.applications.services import calc_annuity


def test_calc_annuity_returns_expected_payment():
    payment = calc_annuity(Decimal("100000"), Decimal("12"), 12)
    assert Decimal("8800") < payment < Decimal("8900")


def test_calc_annuity_zero_rate_splits_evenly():
    payment = calc_annuity(Decimal("120000"), Decimal("0"), 12)
    assert payment == Decimal("10000.00")
