from django.core.cache import cache
from rest_framework.permissions import BasePermission

from apps.rbac.models import Permission

USER_PERMS_CACHE_TTL = 300  # seconds, Doc 3 §5.1


def get_user_permissions(user) -> set:
    """Resolves the full permission-code set held by `user`, caching in Redis.

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
    return perms


def user_has_permission(user, perm_code: str) -> bool:
    """Checks whether `user` holds `perm_code` (see get_user_permissions)."""
    return perm_code in get_user_permissions(user)


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
