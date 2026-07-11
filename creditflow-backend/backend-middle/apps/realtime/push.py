from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def _send(user_id, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f"user_{user_id}",
        {"type": "notify", "payload": payload},
    )


def push_status(application):
    """Doc 3 §7.3: notifies the applicant's WS group of an application status change."""
    _send(application.user_id, {
        "event": "application_status",
        "application_id": application.id,
        "status": application.status,
    })


def push_notification(user_id, notification):
    """Doc 3 §7.3/§11: notifies a user's WS group of a new in-app notification.
    Wired from apps.notifications.services.notify_user (Этап 6)."""
    _send(user_id, {
        "event": "notification",
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "body": notification.body,
    })
