import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def mark_overdue_payments():
    """Doc 3 §12: daily sweep. PENDING instalments whose due_date has passed
    become OVERDUE; any loan that now has an OVERDUE instalment is itself
    flagged OVERDUE. Notifies the borrower for each newly-overdue instalment."""
    from apps.notifications.services import notify_user

    from .models import Loan, PaymentScheduleItem

    today = timezone.now().date()
    overdue_items = list(
        PaymentScheduleItem.objects.filter(due_date__lt=today, status="PENDING").select_related("loan__user")
    )
    if not overdue_items:
        return 0

    with transaction.atomic():
        item_ids = [item.id for item in overdue_items]
        PaymentScheduleItem.objects.filter(id__in=item_ids).update(status="OVERDUE")

        loan_ids = {item.loan_id for item in overdue_items}
        Loan.objects.filter(id__in=loan_ids, status="ACTIVE").update(status="OVERDUE")

    for item in overdue_items:
        notify_user(item.loan.user, "payment.overdue", item)

    return len(overdue_items)
