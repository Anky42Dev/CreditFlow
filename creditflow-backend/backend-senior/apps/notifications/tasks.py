import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Maps a notif_type prefix to the model it's rendered from, so send_email_async
# can look the object back up from just (notif_type, obj_id).
_OBJECT_LOOKUP = {
    "application.": ("apps.applications.models", "CreditApplication"),
    "loan.": ("apps.lending.models", "Loan"),
    "payment.": ("apps.lending.models", "PaymentScheduleItem"),
}


def _resolve_object(notif_type: str, obj_id):
    for prefix, (module_path, model_name) in _OBJECT_LOOKUP.items():
        if notif_type.startswith(prefix):
            module = __import__(module_path, fromlist=[model_name])
            model = getattr(module, model_name)
            try:
                return model.objects.get(id=obj_id)
            except model.DoesNotExist:
                return None
    return None


def build_email(notif_type: str, obj_id):
    """Doc 3 §11: builds (subject, body) for send_email_async from the notif_type
    and the id of the object that triggered it."""
    from .services import DEFAULT_TITLE, TITLES, render_body

    obj = _resolve_object(notif_type, obj_id)
    subject = TITLES.get(notif_type, DEFAULT_TITLE)
    body = render_body(notif_type, obj) if obj is not None else subject
    return subject, body


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_email_async(self, email, notif_type, obj_id):
    try:
        subject, body = build_email(notif_type, obj_id)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
    except Exception as exc:
        logger.exception(
            "send_email_async failed for email=%s notif_type=%s (attempt %s/%s)",
            email, notif_type, self.request.retries + 1, self.max_retries,
        )
        raise self.retry(exc=exc)


@shared_task
def send_due_reminders():
    """Doc 3 §12: 3 days before due_date, notify+email the borrower of an
    upcoming instalment. This task is scheduled once daily, so each item is
    only ever 3-days-out on a single run."""
    from apps.lending.models import PaymentScheduleItem

    from .services import notify_user

    target_date = (timezone.now() + timedelta(days=3)).date()
    items = PaymentScheduleItem.objects.filter(
        due_date=target_date, status="PENDING"
    ).select_related("loan__user")
    for item in items:
        notify_user(item.loan.user, "payment.due", item)
