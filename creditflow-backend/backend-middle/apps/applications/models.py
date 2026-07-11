from django.db import models
from django.db.models import Q

from apps.accounts.models import User
from apps.products.models import CreditProduct


class CreditApplication(models.Model):
    """Doc 3 §1, §6.3: state machine extended with MANUAL_REVIEW and DISBURSED.

    DISBURSED is set by Этап 4's disburse_loan, not by this stage's scoring.
    """

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("SCORING", "Scoring"),
        ("APPROVED", "Approved"),
        ("MANUAL_REVIEW", "Manual review"),
        ("REJECTED", "Rejected"),
        ("DISBURSED", "Disbursed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications", db_index=True)
    product = models.ForeignKey(
        CreditProduct, on_delete=models.PROTECT, related_name="applications", db_index=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    term_months = models.PositiveSmallIntegerField()
    purpose = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT", db_index=True)
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "credit_applications"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="application_amount_gt_0"),
            models.CheckConstraint(condition=Q(term_months__gte=1), name="application_term_gte_1"),
        ]

    def __str__(self):
        return f"Application<{self.id}> {self.status}"


class ScoringResult(models.Model):
    DECISION_CHOICES = [
        ("APPROVED", "Approved"),
        ("MANUAL_REVIEW", "Manual review"),
        ("REJECTED", "Rejected"),
    ]

    application = models.OneToOneField(
        CreditApplication, on_delete=models.CASCADE, related_name="scoring_result"
    )
    score = models.PositiveSmallIntegerField()
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scoring_results"
        constraints = [
            models.CheckConstraint(condition=Q(score__lte=1000), name="scoring_score_lte_1000"),
        ]

    def __str__(self):
        return f"Scoring<{self.application_id}> {self.decision}"


class Document(models.Model):
    """Doc 3 §3.6: a document attached to an application (income proof, ID, ...).
    Uploaded/reviewed via the Этап 7 admin API; no client-facing upload endpoint yet."""

    application = models.ForeignKey(
        CreditApplication, on_delete=models.CASCADE, related_name="documents", db_index=True
    )
    file = models.FileField(upload_to="documents/")
    doc_type = models.CharField(max_length=40)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents"

    def __str__(self):
        return f"Document<{self.application_id}> {self.doc_type}"
