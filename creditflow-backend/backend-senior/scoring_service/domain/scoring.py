"""DOC 5 §7.1-7.2: the scoring domain — no Django, no HTTP, no broker.

Ports apps.applications.services.compute_score + decide (backend-senior,
Doc 3 §6.3) heuristic verbatim: same thresholds, same ratio bands, same
decision reasons. Kept as an independent copy rather than importing the
Django code (DOC 5 §7.1: this service has its own release cycle and must
run without the Django project installed) — see scoring_service/tests/
contract/test_scoring_parity.py for the test asserting the two stay in sync.
"""

from dataclasses import dataclass
from decimal import Decimal

SCORE_APPROVED_THRESHOLD = 700
SCORE_MANUAL_REVIEW_THRESHOLD = 500

APPROVED = "APPROVED"
MANUAL_REVIEW = "MANUAL_REVIEW"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class ScoringInput:
    application_id: int
    monthly_payment: Decimal
    monthly_income: Decimal | None
    has_birth_date: bool


@dataclass(frozen=True)
class ScoreResult:
    application_id: int
    score: int
    decision: str
    reason: str


class ScoringEngine:
    """Stateless: a fresh evaluation per request/message, no shared mutable
    state — safe to call concurrently from multiple async requests/consumer
    workers."""

    @staticmethod
    def evaluate(scoring_input: ScoringInput) -> ScoreResult:
        score = 500
        # Zero and missing income are treated alike (no ratio signal) —
        # mirrors compute_score's "no income declared" handling.
        if scoring_input.monthly_income:
            ratio = scoring_input.monthly_payment / scoring_input.monthly_income
            if ratio < Decimal("0.2"):
                score += 300
            elif ratio < Decimal("0.4"):
                score += 100
            else:
                score -= 200
        if not scoring_input.has_birth_date:
            score -= 100
        score = max(0, min(1000, score))

        decision, reason = ScoringEngine._decide(score)
        return ScoreResult(
            application_id=scoring_input.application_id,
            score=score,
            decision=decision,
            reason=reason,
        )

    @staticmethod
    def _decide(score: int) -> tuple[str, str]:
        if score >= SCORE_APPROVED_THRESHOLD:
            return APPROVED, "Sufficient income"
        elif score >= SCORE_MANUAL_REVIEW_THRESHOLD:
            return MANUAL_REVIEW, "Borderline score, needs underwriter review"
        return REJECTED, "High debt-to-income or missing data"
