from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """DOC 5 §4.1. `currency` is a fixed default: the current schema
    (apps/products, apps/applications) stores plain DecimalFields with no
    per-record currency column, so every Money in this system is implicitly KGS.
    """

    amount: Decimal
    currency: str = "KGS"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money cannot be negative")

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __le__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount <= other.amount

    def __ge__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount >= other.amount
