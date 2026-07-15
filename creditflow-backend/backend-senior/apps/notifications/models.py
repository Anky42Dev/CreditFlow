from django.db import models

from apps.accounts.models import User


class Notification(models.Model):
    """Doc 3 §3.5: in-app notification, mirrored by a WS push and an async email."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications", db_index=True)
    type = models.CharField(max_length=40)
    title = models.CharField(max_length=120)
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"Notification<{self.user_id}> {self.type}"
