from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL

from apps.accounts.models import User
from apps.applications.models import CreditApplication


class Loan(models.Model):
    """Doc 3 §3.2, §9.1: credit agreement created by disburse_loan on APPROVED scoring."""

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
        ("OVERDUE", "Overdue"),
    ]

    application = models.OneToOneField(
        CreditApplication, on_delete=models.PROTECT, related_name="loan"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="loans", db_index=True)
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_months = models.PositiveSmallIntegerField()
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE", db_index=True)
    disbursed_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "loans"
        constraints = [
            models.CheckConstraint(condition=Q(principal__gt=0), name="loan_principal_gt_0"),
            models.CheckConstraint(condition=Q(term_months__gte=1), name="loan_term_gte_1"),
        ]

    def __str__(self):
        return f"Loan<{self.id}> {self.status}"


class PaymentScheduleItem(models.Model):
    """Doc 3 §3.3: one instalment of a loan's amortization schedule."""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="schedule_items", db_index=True)
    sequence = models.PositiveSmallIntegerField()
    due_date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    principal_part = models.DecimalField(max_digits=12, decimal_places=2)
    interest_part = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_schedule_items"
        constraints = [
            models.UniqueConstraint(fields=["loan", "sequence"], name="unique_loan_sequence"),
        ]
        ordering = ["sequence"]

    def __str__(self):
        return f"Schedule<{self.loan_id}:{self.sequence}> {self.status}"


class Transaction(models.Model):
    """Doc 3 §3.4: money movement ledger for a loan (disbursement/repayment).

    DOC 5 §14, Roadmap Этап 5 п.14: partitioned by month on `created_at`
    (see migration 0003) — the fastest-growing ledger table. Postgres
    requires the partition key in every unique constraint (including the
    PK), so `id` can no longer be a lone AutoField PK: it's a plain
    BigIntegerField whose value comes from a DB sequence
    (`transactions_id_seq`, created in the same migration) via `db_default`,
    and the real PK is the composite (id, created_at) below.

    Trade-off: `idempotency_key` uniqueness becomes (idempotency_key,
    created_at) instead of a lone global unique — the same key could only
    collide with an already-committed key if it also landed in the exact
    same microsecond `created_at`, which is not a realistic collision for
    request-scoped idempotency checks (apps.lending.services checks-then-
    creates within one transaction).
    """

    TYPE_CHOICES = [
        ("DISBURSEMENT", "Disbursement"),
        ("REPAYMENT", "Repayment"),
        ("INTEREST_ACCRUAL", "Interest accrual"),
    ]

    id = models.BigIntegerField(
        editable=False, db_default=RawSQL("nextval('transactions_id_seq')", [])
    )
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="transactions", db_index=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    pk = models.CompositePrimaryKey("id", "created_at")

    class Meta:
        db_table = "transactions"
        indexes = [
            # DOC 5 §14: a loan's ledger read in chronological order (Loan
            # detail's transactions prefetch) — beats separate loan/created_at
            # single-column indexes for this query shape.
            models.Index(fields=["loan", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key", "created_at"], name="unique_transaction_idempotency_key"
            ),
        ]

    def __str__(self):
        return f"Transaction<{self.loan_id}> {self.type} {self.amount}"
