from decimal import Decimal

from ..value_objects.application_status import ApplicationStatus

SCORE_APPROVED_THRESHOLD = 700
SCORE_MANUAL_REVIEW_THRESHOLD = 500


class ScoringPolicy:
    """DOC 5 §4.2 domain service. Pure score math extracted from
    apps.applications.services.compute_score/perform_scoring (Doc 3 §6.3).

    `compute_score` takes an already-derived payment-to-income ratio rather than
    a Django Profile, so it has no ORM dependency; deriving that ratio (which
    needs `application.user.profile`) stays an application/infrastructure-layer
    concern until Этап 2 wires a real scoring use case.
    """

    @staticmethod
    def compute_score(
        payment_to_income_ratio: Decimal | None, has_birth_date: bool
    ) -> int:
        score = 500
        # Zero and missing income are treated alike (no ratio signal) — a Profile
        # with monthly_income=0 is drawn from the same "no income declared" corpus.
        if payment_to_income_ratio is not None:
            if payment_to_income_ratio < Decimal("0.2"):
                score += 300
            elif payment_to_income_ratio < Decimal("0.4"):
                score += 100
            else:
                score -= 200
        if not has_birth_date:
            score -= 100
        return max(0, min(1000, score))

    @staticmethod
    def decide(score: int) -> ApplicationStatus:
        if score >= SCORE_APPROVED_THRESHOLD:
            return ApplicationStatus.APPROVED
        if score >= SCORE_MANUAL_REVIEW_THRESHOLD:
            return ApplicationStatus.MANUAL_REVIEW
        return ApplicationStatus.REJECTED
