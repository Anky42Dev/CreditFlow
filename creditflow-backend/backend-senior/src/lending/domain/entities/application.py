from shared.domain.aggregate_root import AggregateRoot
from shared.domain.errors import DomainError

from ..events.application_approved import ApplicationApproved
from ..events.application_rejected import ApplicationRejected
from ..events.application_submitted import ApplicationSubmitted
from ..value_objects.application_status import ApplicationStatus
from ..value_objects.money import Money
from ..value_objects.term import Term
from .product import CreditProduct


class CreditApplicationAggregate(AggregateRoot):
    """DOC 5 §4.2. Aggregate root for the CreditApplication bounded context.

    Ported from apps.applications.models.CreditApplication's state machine and
    apps.applications.services' submit_application/perform_scoring/
    approve_application/reject_application — business rules only. Persistence
    (ORM save, AuditLog, outbox), notifications and the realtime push are
    infrastructure/application-layer concerns wired in Этап 2+, not here.
    """

    def __init__(
        self,
        id,
        user_id,
        product: CreditProduct,
        amount: Money,
        term: Term,
        status: ApplicationStatus = ApplicationStatus.DRAFT,
        monthly_payment: Money | None = None,
    ):
        super().__init__(id)
        self.user_id = user_id
        self.product = product
        self.amount = amount
        self.term = term
        self.status = status
        self.monthly_payment = monthly_payment

    def submit(self) -> None:
        """Doc 3 §6.2: DRAFT -> SUBMITTED, computing the annuity payment."""
        if self.status != ApplicationStatus.DRAFT:
            raise DomainError("Only DRAFT applications can be submitted")
        self.product.validate_amount(self.amount)
        self.product.validate_term(self.term)
        self.monthly_payment = self.product.calc_annuity(self.amount, self.term)
        self._transition(ApplicationStatus.SUBMITTED)
        self.raise_event(
            ApplicationSubmitted(application_id=self.id, user_id=self.user_id)
        )

    def start_scoring(self) -> None:
        """Doc 3 §6.3: SUBMITTED -> SCORING, entered when the async scoring task picks up the application."""
        self._transition(ApplicationStatus.SCORING)

    def apply_scoring_decision(self, decision: ApplicationStatus) -> None:
        """Doc 3 §6.3: SCORING -> {APPROVED, MANUAL_REVIEW, REJECTED} per the scoring result."""
        if decision not in (
            ApplicationStatus.APPROVED,
            ApplicationStatus.MANUAL_REVIEW,
            ApplicationStatus.REJECTED,
        ):
            raise DomainError(f"{decision} is not a valid scoring decision")
        self._transition(decision)
        if decision == ApplicationStatus.APPROVED:
            self.raise_event(
                ApplicationApproved(
                    application_id=self.id, user_id=self.user_id, amount=self.amount
                )
            )
        elif decision == ApplicationStatus.REJECTED:
            self.raise_event(
                ApplicationRejected(application_id=self.id, user_id=self.user_id)
            )

    def approve_from_manual_review(self) -> None:
        """Doc 3 §10: underwriter approval of a MANUAL_REVIEW application."""
        if self.status != ApplicationStatus.MANUAL_REVIEW:
            raise DomainError("Only MANUAL_REVIEW applications can be approved")
        self._transition(ApplicationStatus.APPROVED)
        self.raise_event(
            ApplicationApproved(
                application_id=self.id, user_id=self.user_id, amount=self.amount
            )
        )

    def reject_from_manual_review(self) -> None:
        """Doc 3 §10: underwriter rejection of a MANUAL_REVIEW application."""
        if self.status != ApplicationStatus.MANUAL_REVIEW:
            raise DomainError("Only MANUAL_REVIEW applications can be rejected")
        self._transition(ApplicationStatus.REJECTED)
        self.raise_event(
            ApplicationRejected(application_id=self.id, user_id=self.user_id)
        )

    def mark_disbursed(self) -> None:
        """APPROVED -> DISBURSED, set by apps.lending.services.disburse_loan (Payments BC)."""
        self._transition(ApplicationStatus.DISBURSED)

    def _transition(self, target: ApplicationStatus) -> None:
        if not self.status.can_transition_to(target):
            raise DomainError(f"Invalid transition {self.status} -> {target}")
        self.status = target
