from decimal import Decimal

from lending.domain.services.scoring_policy import ScoringPolicy
from lending.domain.value_objects.application_status import ApplicationStatus


def test_high_income_low_ratio_scores_high():
    # apps.applications.tests.ComputeScoreTests.test_high_income_low_ratio_scores_high:
    # ratio 18000/100000 = 0.18 < 0.2 -> +300, birth_date present -> no penalty.
    score = ScoringPolicy.compute_score(
        Decimal("18000") / Decimal("100000"), has_birth_date=True
    )
    assert score == 800


def test_missing_income_and_birth_date_scores_low():
    # apps.applications.tests.ComputeScoreTests.test_missing_income_and_birth_date_scores_low
    score = ScoringPolicy.compute_score(None, has_birth_date=False)
    assert score == 400


def test_mid_ratio_adds_partial():
    score = ScoringPolicy.compute_score(Decimal("0.3"), has_birth_date=True)
    assert score == 600


def test_high_ratio_penalized():
    score = ScoringPolicy.compute_score(Decimal("0.5"), has_birth_date=True)
    assert score == 300


def test_score_clamped_between_0_and_1000():
    assert ScoringPolicy.compute_score(Decimal("0.5"), has_birth_date=False) == 200


def test_decide_approved_at_threshold():
    assert ScoringPolicy.decide(700) == ApplicationStatus.APPROVED


def test_decide_manual_review_at_threshold():
    assert ScoringPolicy.decide(500) == ApplicationStatus.MANUAL_REVIEW


def test_decide_rejected_below_threshold():
    assert ScoringPolicy.decide(499) == ApplicationStatus.REJECTED
