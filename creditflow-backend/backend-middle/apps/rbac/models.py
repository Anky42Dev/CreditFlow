from django.conf import settings
from django.db import models


class Role(models.Model):
    """Doc 3 §3.1. Explicit RBAC role, distinct from User.role (denormalized pointer)."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.code


class Permission(models.Model):
    """Doc 3 §3.1. e.g. code='application.approve'."""

    code = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="unique_role_permission"),
        ]

    def __str__(self):
        return f"{self.role_id}:{self.permission_id}"


class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        db_table = "user_roles"
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="unique_user_role"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.role_id}"
