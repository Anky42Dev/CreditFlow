from django.db import models
from django.db.models import Q

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
    """Doc 3 §3.4: money movement ledger for a loan (disbursement/repayment)."""

    TYPE_CHOICES = [
        ("DISBURSEMENT", "Disbursement"),
        ("REPAYMENT", "Repayment"),
        ("INTEREST_ACCRUAL", "Interest accrual"),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="transactions", db_index=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = "transactions"

    def __str__(self):
        return f"Transaction<{self.loan_id}> {self.type} {self.amount}"
