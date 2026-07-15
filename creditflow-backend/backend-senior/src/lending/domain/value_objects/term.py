from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    """DOC 5 §4.1: loan term in months. Mirrors CreditApplication.term_months
    (PositiveSmallIntegerField) — the >=1 rule is the same one enforced at the
    DB level by the `application_term_gte_1` CheckConstraint.
    """

    months: int

    def __post_init__(self):
        if self.months < 1:
            raise ValueError("Term must be at least 1 month")
