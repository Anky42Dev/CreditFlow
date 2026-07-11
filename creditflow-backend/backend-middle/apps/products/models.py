from django.db import models
from django.db.models import F, Q


class CreditProduct(models.Model):
    """Doc 1 §... / Doc 3 §1: same schema as Junior, reused by Middle's async scoring."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, db_index=True)
    description = models.TextField(blank=True)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    min_term_months = models.PositiveSmallIntegerField()
    max_term_months = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "credit_products"
        constraints = [
            models.CheckConstraint(condition=Q(max_amount__gte=F("min_amount")), name="max_gte_min_amount"),
            models.CheckConstraint(condition=Q(max_term_months__gte=F("min_term_months")), name="max_gte_min_term"),
            models.CheckConstraint(
                condition=Q(interest_rate__gte=0) & Q(interest_rate__lte=100), name="rate_0_100"
            ),
        ]
        indexes = [models.Index(fields=["is_active", "slug"])]

    def __str__(self):
        return self.name
