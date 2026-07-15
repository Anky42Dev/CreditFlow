from enum import Enum

# DOC 5 §4.1 puts this table as an Enum class attribute; a plain dict assigned
# inside an Enum body is instead picked up as a spurious extra member (Python
# `enum` treats any non-callable class attribute as a value), so it lives
# module-level here and is looked up by value in can_transition_to.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"SCORING"},
    "SCORING": {"APPROVED", "REJECTED", "MANUAL_REVIEW"},
    "MANUAL_REVIEW": {"APPROVED", "REJECTED"},
    "APPROVED": {"DISBURSED"},
}


class ApplicationStatus(str, Enum):
    """DOC 5 §4.1. Mirrors CreditApplication.STATUS_CHOICES
    (apps/applications/models.py) and the transitions actually driven by
    apps/applications/services.py (submit_application, perform_scoring,
    approve_application, reject_application) plus apps/lending/services.py's
    disburse_loan (APPROVED -> DISBURSED).
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    SCORING = "SCORING"
    APPROVED = "APPROVED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECTED = "REJECTED"
    DISBURSED = "DISBURSED"

    def can_transition_to(self, target: "ApplicationStatus") -> bool:
        return target.value in _ALLOWED_TRANSITIONS.get(self.value, set())
