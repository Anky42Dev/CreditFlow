from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.exceptions import ConflictError

from .models import CreditApplication, ScoringResult


def calc_annuity(amount: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    r = annual_rate / Decimal(100) / Decimal(12)
    if r == 0:
        return (amount / months).quantize(Decimal("0.01"))
    factor = (1 + r) ** months
    payment = amount * r * factor / (factor - 1)
    return payment.quantize(Decimal("0.01"))


def validate_amount_and_term(product, amount, term_months) -> None:
    if not (product.min_amount <= amount <= product.max_amount):
        raise ValidationError({"amount": [f"Must be between {product.min_amount} and {product.max_amount}"]})
    if not (product.min_term_months <= term_months <= product.max_term_months):
        raise ValidationError(
            {"term_months": [f"Must be between {product.min_term_months} and {product.max_term_months}"]}
        )


def submit_application(application: CreditApplication) -> CreditApplication:
    if application.status != "DRAFT":
        raise ConflictError(message="Only DRAFT applications can be submitted")

    validate_amount_and_term(application.product, application.amount, application.term_months)

    application.monthly_payment = calc_annuity(
        application.amount, application.product.interest_rate, application.term_months
    )
    application.status = "SUBMITTED"
    application.submitted_at = timezone.now()
    application.save()

    run_scoring(application)
    return application


def run_scoring(application: CreditApplication) -> ScoringResult:
    application.status = "SCORING"
    application.save(update_fields=["status"])

    profile = application.user.profile
    score = 500
    if profile.monthly_income:
        ratio = application.monthly_payment / profile.monthly_income
        if ratio < Decimal("0.2"):
            score += 300
        elif ratio < Decimal("0.4"):
            score += 100
        else:
            score -= 200
    if profile.birth_date is None:
        score -= 100

    score = max(0, min(1000, score))
    decision = "APPROVED" if score >= 600 else "REJECTED"
    reason = "Sufficient income" if decision == "APPROVED" else "High debt-to-income or missing data"

    application.status = decision
    application.save(update_fields=["status"])

    return ScoringResult.objects.create(
        application=application, score=score, decision=decision, reason=reason
    )
