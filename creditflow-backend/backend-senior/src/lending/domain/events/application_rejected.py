from dataclasses import dataclass

from shared.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class ApplicationRejected(DomainEvent):
    """DOC 5 §4.3. Raised when scoring decides REJECTED, or an underwriter
    rejects a MANUAL_REVIEW application (apps/applications/services.py
    perform_scoring / reject_application).
    """

    application_id: int
    user_id: int
