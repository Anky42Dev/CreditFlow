from django.core.cache import cache
from rest_framework.permissions import BasePermission

from apps.rbac.models import Permission

USER_PERMS_CACHE_TTL = 300  # seconds, Doc 3 §5.1


def user_has_permission(user, perm_code: str) -> bool:
    """Checks whether `user` holds `perm_code`, caching the resolved set in Redis.

    Cache invalidated by apps.rbac.services.assign_role/revoke_role.
    """
    cache_key = f"user_perms:{user.id}"
    perms = cache.get(cache_key)
    if perms is None:
        perms = set(
            Permission.objects.filter(
                rolepermission__role__userrole__user=user
            ).values_list("code", flat=True)
        )
        cache.set(cache_key, perms, USER_PERMS_CACHE_TTL)
    return perm_code in perms


class HasPermission(BasePermission):
    """View-level permission gate. Set `required_permission = "code"` on the view."""

    required_permission = None

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        perm = getattr(view, "required_permission", None)
        if perm is None:
            return True
        return user_has_permission(request.user, perm)
