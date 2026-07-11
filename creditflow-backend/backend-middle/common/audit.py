def get_client_ip(request):
    """Best-effort client IP extraction; None when there's no request (system events)."""
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit_log(actor, action, obj, changes=None, request=None):
    """Doc 3 §14. `actor` may be a User, None (system-initiated action), or
    AnonymousUser -- the latter two are both stored as actor=None.
    """
    from apps.audit.models import AuditLog

    resolved_actor = actor if getattr(actor, "pk", None) else None

    AuditLog.objects.create(
        actor=resolved_actor,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=obj.pk,
        changes=changes or {},
        ip_address=get_client_ip(request),
    )
