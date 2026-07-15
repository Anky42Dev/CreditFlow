from decimal import Decimal

from shared.domain.entity import Entity
from shared.domain.errors import DomainError

from ..value_objects.money import Money
from ..value_objects.term import Term


class CreditProduct(Entity):
    """DOC 5 §4.2. Ported from apps.products.models.CreditProduct +
    apps.applications.services.validate_amount_and_term/calc_annuity
    (Doc 3 §1/§6.2) — same rules, no Django/Decimal-from-string parsing here,
    just the pure math and bounds checks.
    """

    def __init__(
        self,
        id: int,
        min_amount: Money,
        max_amount: Money,
        interest_rate: Decimal,
        min_term_months: int,
        max_term_months: int,
        is_active: bool = True,
    ):
        super().__init__(id)
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.interest_rate = interest_rate
        self.min_term_months = min_term_months
        self.max_term_months = max_term_months
        self.is_active = is_active

    def validate_amount(self, amount: Money) -> None:
        if not (self.min_amount.amount <= amount.amount <= self.max_amount.amount):
            raise DomainError(
                f"Amount must be between {self.min_amount.amount} and {self.max_amount.amount}"
            )

    def validate_term(self, term: Term) -> None:
        if not (self.min_term_months <= term.months <= self.max_term_months):
            raise DomainError(
                f"Term must be between {self.min_term_months} and {self.max_term_months} months"
            )

    def calc_annuity(self, amount: Money, term: Term) -> Money:
        rate = self.interest_rate / Decimal(100) / Decimal(12)
        months = term.months
        if rate == 0:
            payment = amount.amount / months
        else:
            factor = (1 + rate) ** months
            payment = amount.amount * rate * factor / (factor - 1)
        return Money(payment.quantize(Decimal("0.01")), amount.currency)
