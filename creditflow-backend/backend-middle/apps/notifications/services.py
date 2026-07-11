from django.core.cache import cache

from .models import Notification

# Doc 3 §11: title per notif_type. Falls back to a generic title for unmapped types
# so a new type doesn't crash notify_user — only a slightly generic notification.
TITLES = {
    "application.approved": "Заявка одобрена",
    "application.manual_review": "Заявка на ручной проверке",
    "application.rejected": "Заявка отклонена",
    "application.documents_requested": "Запрошены документы",
    "loan.disbursed": "Кредит выдан",
    "payment.due": "Скоро платёж по кредиту",
    "payment.overdue": "Платёж просрочен",
}
DEFAULT_TITLE = "Уведомление"


def render_body(notif_type: str, obj) -> str:
    """Doc 3 §11: renders the notification body from the triggering object.

    `obj` is a CreditApplication for application.*, a Loan for loan.disbursed,
    and a PaymentScheduleItem for payment.*.
    """
    if notif_type == "application.approved":
        return f"Ваша заявка №{obj.id} на сумму {obj.amount} одобрена."
    if notif_type == "application.manual_review":
        return f"Заявка №{obj.id} передана на ручную проверку андеррайтером."
    if notif_type == "application.rejected":
        return f"Заявка №{obj.id} отклонена."
    if notif_type == "application.documents_requested":
        return f"По заявке №{obj.id} запрошены дополнительные документы. Пожалуйста, загрузите их в личном кабинете."
    if notif_type == "loan.disbursed":
        return f"Кредит №{obj.id} на сумму {obj.principal} выдан на ваш счёт."
    if notif_type == "payment.due":
        return f"Платёж {obj.amount} по кредиту №{obj.loan_id} ожидается {obj.due_date}."
    if notif_type == "payment.overdue":
        return f"Платёж {obj.amount} по кредиту №{obj.loan_id} просрочен (срок был {obj.due_date})."
    return f"{notif_type}: {obj}"


def notify_user(user, notif_type: str, obj) -> Notification:
    """Doc 3 §11: creates the in-app Notification, pushes it over WS, queues the
    email, and invalidates the cached unread-count so the next GET recomputes it."""
    from apps.realtime.push import push_notification

    from .tasks import send_email_async

    notification = Notification.objects.create(
        user=user,
        type=notif_type,
        title=TITLES.get(notif_type, DEFAULT_TITLE),
        body=render_body(notif_type, obj),
    )
    push_notification(user.id, notification)
    send_email_async.delay(user.email, notif_type, obj.id)
    cache.delete(f"unread:{user.id}")
    return notification
