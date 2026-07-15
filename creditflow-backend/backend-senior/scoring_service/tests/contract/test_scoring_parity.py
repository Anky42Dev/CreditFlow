"""DOC 5 §7.1: scoring_service.domain.scoring.ScoringEngine is an independent
*copy* of apps.applications.services.compute_score + decide (backend-senior,
Doc 3 §6.3) — not a shared import, since the two are separate deployables
with separate release cycles. This test hardcodes the same input/output
pairs the Django-side test suite exercises (tests_integration.py /
apps/applications/tests.py use the `user` fixture: monthly_income=100000.00,
birth_date=1990-01-01) so a future edit to either implementation's
thresholds/ratio-bands is caught here as a parity break, not discovered in
production as a Django/scoring_service disagreement.

If this test ever needs updating, the same change must be mirrored in
apps/applications/services.py::compute_score/decide on the Django side (and
vice versa) — that's the whole point of the contract.
"""

from decimal import Decimal

import pytest

from scoring_service.domain.scoring import ScoringEngine, ScoringInput

# (monthly_payment, monthly_income, has_birth_date) -> (score, decision)
# Mirrors apps.applications.services.compute_score's ratio bands
# (<0.2 -> +300, <0.4 -> +100, else -200) and birth_date penalty (-100),
# and decide()'s thresholds (>=700 APPROVED, >=500 MANUAL_REVIEW, else REJECTED).
PARITY_CASES = [
    (Decimal("18300.00"), Decimal("100000.00"), True, 800, "APPROVED"),
    (Decimal("30000.00"), Decimal("100000.00"), True, 600, "MANUAL_REVIEW"),
    (Decimal("60000.00"), Decimal("100000.00"), True, 300, "REJECTED"),
    (Decimal("10000.00"), None, True, 500, "MANUAL_REVIEW"),
    (Decimal("10000.00"), Decimal("100000.00"), False, 700, "APPROVED"),
]


@pytest.mark.parametrize(
    "monthly_payment,monthly_income,has_birth_date,expected_score,expected_decision",
    PARITY_CASES,
)
def test_scoring_engine_matches_documented_django_parity_cases(
    monthly_payment, monthly_income, has_birth_date, expected_score, expected_decision
):
    result = ScoringEngine.evaluate(
        ScoringInput(
            application_id=1,
            monthly_payment=monthly_payment,
            monthly_income=monthly_income,
            has_birth_date=has_birth_date,
        )
    )
    assert result.score == expected_score
    assert result.decision == expected_decision
