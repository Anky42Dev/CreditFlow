from django.core.cache import cache
from django.db import transaction

from common.audit import audit_log

from .models import Role, UserRole


def _invalidate_perms_cache(user_id):
    cache.delete(f"user_perms:{user_id}")


@transaction.atomic
def assign_role(user, role_code: str, actor=None, request=None):
    """Grants `role_code` to `user` and syncs the denormalized User.role pointer.

    Doc 3 §3.1: User.role stays a fast denormalized pointer to the primary
    role; the UserRole table is the source of truth for detailed RBAC.

    `actor`/`request` are optional (default None) so existing callers/tests
    keep working; pass them once the admin "change user role" endpoint
    (Промпт №3/№7) calls this.
    """
    role = Role.objects.get(code=role_code)
    UserRole.objects.get_or_create(user=user, role=role)
    if user.role != role_code:
        user.role = role_code
        user.save(update_fields=["role"])
    _invalidate_perms_cache(user.id)
    audit_log(actor, "user.role_assigned", user, changes={"role": role_code}, request=request)
    return user


@transaction.atomic
def revoke_role(user, role_code: str, actor=None, request=None):
    UserRole.objects.filter(user=user, role__code=role_code).delete()
    _invalidate_perms_cache(user.id)
    audit_log(actor, "user.role_revoked", user, changes={"role": role_code}, request=request)
    return user
