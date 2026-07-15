from decimal import Decimal

import pytest

from scoring_service.domain.scoring import (
    APPROVED,
    MANUAL_REVIEW,
    REJECTED,
    ScoringEngine,
    ScoringInput,
)


def test_low_payment_to_income_ratio_is_approved():
    result = ScoringEngine.evaluate(
        ScoringInput(
            application_id=1,
            monthly_payment=Decimal("10000"),
            monthly_income=Decimal("100000"),
            has_birth_date=True,
        )
    )
    assert result.decision == APPROVED
    assert result.score == 800
    assert result.reason == "Sufficient income"


def test_mid_payment_to_income_ratio_is_manual_review():
    result = ScoringEngine.evaluate(
        ScoringInput(
            application_id=2,
            monthly_payment=Decimal("30000"),
            monthly_income=Decimal("100000"),
            has_birth_date=True,
        )
    )
    assert result.decision == MANUAL_REVIEW
    assert result.score == 600


def test_high_payment_to_income_ratio_is_rejected():
    result = ScoringEngine.evaluate(
        ScoringInput(
            application_id=3,
            monthly_payment=Decimal("60000"),
            monthly_income=Decimal("100000"),
            has_birth_date=True,
        )
    )
    assert result.decision == REJECTED
    assert result.score == 300


def test_missing_income_degrades_like_zero_income():
    with_none = ScoringEngine.evaluate(
        ScoringInput(
            application_id=4,
            monthly_payment=Decimal("1000"),
            monthly_income=None,
            has_birth_date=True,
        )
    )
    with_zero = ScoringEngine.evaluate(
        ScoringInput(
            application_id=4,
            monthly_payment=Decimal("1000"),
            monthly_income=Decimal("0"),
            has_birth_date=True,
        )
    )
    assert with_none.score == with_zero.score == 500
    assert with_none.decision == MANUAL_REVIEW


def test_missing_birth_date_penalizes_score():
    result = ScoringEngine.evaluate(
        ScoringInput(
            application_id=5,
            monthly_payment=Decimal("10000"),
            monthly_income=Decimal("100000"),
            has_birth_date=False,
        )
    )
    assert result.score == 700  # 500 + 300 - 100
    assert result.decision == APPROVED


@pytest.mark.parametrize(
    "payment,income", [(Decimal("999999"), Decimal("1")), (Decimal("1"), Decimal("1"))]
)
def test_score_never_leaves_0_1000_bounds(payment, income):
    result = ScoringEngine.evaluate(
        ScoringInput(
            application_id=6,
            monthly_payment=payment,
            monthly_income=income,
            has_birth_date=True,
        )
    )
    assert 0 <= result.score <= 1000
