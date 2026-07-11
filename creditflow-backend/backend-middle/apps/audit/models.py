from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditLog(models.Model):
    """Doc 3 §3.7, §14: immutable trail of significant platform actions.

    `actor` is null for system-initiated events (e.g. async scoring status
    transitions) — see common.audit.audit_log. `object_type`/`object_id`
    are a loose (non-FK) reference so the log survives even if the
    referenced row is later deleted.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
    )
    action = models.CharField(max_length=60, db_index=True)
    object_type = models.CharField(max_length=40)
    object_id = models.BigIntegerField()
    changes = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"AuditLog<{self.action}:{self.object_type}#{self.object_id}>"
