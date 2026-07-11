from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import IntegrityError, transaction
from django.utils import timezone

from common.exceptions import ConflictError

from .models import Loan, PaymentScheduleItem, Transaction


@transaction.atomic
def disburse_loan(application) -> Loan:
    """Doc 3 §9.1. Called from apps.applications.services.perform_scoring on APPROVED.

    Idempotent against retries of the scoring task: if a Loan already exists
    for this application (OneToOne), returns it instead of raising IntegrityError.
    """
    if hasattr(application, "loan"):
        return application.loan

    product = application.product
    loan = Loan.objects.create(
        application=application,
        user=application.user,
        principal=application.amount,
        interest_rate=product.interest_rate,
        term_months=application.term_months,
        monthly_payment=application.monthly_payment,
        outstanding_balance=application.amount,
        status="ACTIVE",
        disbursed_at=timezone.now(),
    )
    build_payment_schedule(loan)
    Transaction.objects.create(
        loan=loan, type="DISBURSEMENT", amount=loan.principal, balance_after=loan.principal,
    )
    application.status = "DISBURSED"
    application.save(update_fields=["status"])

    from apps.notifications.services import notify_user

    notify_user(loan.user, "loan.disbursed", loan)

    return loan


def build_payment_schedule(loan: Loan) -> None:
    """Doc 3 §9.1. Annuity schedule; the last instalment absorbs rounding drift
    so outstanding_balance reaches exactly zero when fully repaid."""
    balance = loan.principal
    rate = loan.interest_rate / Decimal(100) / Decimal(12)
    items = []
    for sequence in range(1, loan.term_months + 1):
        interest_part = (balance * rate).quantize(Decimal("0.01"))
        if sequence == loan.term_months:
            principal_part = balance
        else:
            principal_part = (loan.monthly_payment - interest_part).quantize(Decimal("0.01"))
        balance -= principal_part
        items.append(
            PaymentScheduleItem(
                loan=loan,
                sequence=sequence,
                due_date=loan.disbursed_at.date() + relativedelta(months=sequence),
                amount=principal_part + interest_part,
                principal_part=principal_part,
                interest_part=interest_part,
                status="PENDING",
            )
        )
    PaymentScheduleItem.objects.bulk_create(items)


@transaction.atomic
def repay(loan: Loan, amount: Decimal, idempotency_key: str) -> Loan:
    """Doc 3 §9.2. select_for_update serializes concurrent repayments on the
    same loan, so a retried request with the same idempotency_key blocks
    until the first attempt commits, then observes it and raises ConflictError
    instead of double-crediting. The IntegrityError catch is defense-in-depth
    against a duplicate key racing in from a different loan."""
    loan = Loan.objects.select_for_update().get(id=loan.id)

    if Transaction.objects.filter(idempotency_key=idempotency_key).exists():
        raise ConflictError(code="DUPLICATE", message="Repayment already processed")
    if loan.status == "CLOSED":
        raise ConflictError(message="Loan is already closed")

    loan.outstanding_balance -= amount
    now = timezone.now()
    if loan.outstanding_balance <= 0:
        loan.status = "CLOSED"
        loan.closed_at = now
        # A closing repayment (full or overpaying) settles the whole remaining
        # schedule, not just the nearest instalment — otherwise later items are
        # left PENDING on a CLOSED loan and would misfire overdue detection.
        loan.schedule_items.filter(status="PENDING").update(status="PAID", paid_at=now)
    else:
        item = loan.schedule_items.filter(status="PENDING").order_by("sequence").first()
        if item:
            item.status = "PAID"
            item.paid_at = now
            item.save(update_fields=["status", "paid_at"])
    loan.save()

    try:
        Transaction.objects.create(
            loan=loan, type="REPAYMENT", amount=amount,
            balance_after=loan.outstanding_balance, idempotency_key=idempotency_key,
        )
    except IntegrityError:
        raise ConflictError(code="DUPLICATE", message="Repayment already processed")

    return loan
