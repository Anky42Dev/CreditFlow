from dataclasses import dataclass
from decimal import Decimal

from shared.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class ApplicationSubmitted(DomainEvent):
    """DOC 5 §4.3. Raised by CreditApplicationAggregate.submit()."""

    application_id: int
    user_id: int

    # DOC 5 §7, Roadmap Этап 4: the aggregate itself only ever sets
    # application_id/user_id (Lending-context data only — the aggregate must
    # not know about Identity's Profile). These fields are optional and
    # defaulted to None so aggregate.submit() and the existing unit tests
    # (test_application_aggregate.py) are unaffected; they're filled in by
    # SubmitApplicationUseCase, which enriches the pulled event with the
    # scoring inputs the (external) scoring_service consumer needs, at the
    # domain-event -> integration-event translation boundary.
    amount: Decimal | None = None
    term_months: int | None = None
    monthly_payment: Decimal | None = None
    monthly_income: Decimal | None = None
    has_birth_date: bool | None = None
