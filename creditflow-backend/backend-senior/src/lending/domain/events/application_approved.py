from dataclasses import dataclass

from lending.domain.value_objects.money import Money
from shared.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class ApplicationApproved(DomainEvent):
    """DOC 5 §4.3. Raised when scoring decides APPROVED, or an underwriter
    approves a MANUAL_REVIEW application (apps/applications/services.py
    perform_scoring / approve_application).
    """

    application_id: int
    user_id: int
    amount: Money
