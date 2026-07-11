from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase, override_settings

from apps.accounts.models import User
from common.permissions import user_has_permission
from .models import Permission, Role, RolePermission, UserRole
from .services import assign_role, revoke_role

TEST_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class RoleModelTests(TestCase):
    def test_role_code_is_unique(self):
        Role.objects.create(code="CLIENT", name="Client")
        with self.assertRaises(IntegrityError):
            Role.objects.create(code="CLIENT", name="Client duplicate")


class RolePermissionModelTests(TestCase):
    def test_role_permission_pair_is_unique(self):
        role = Role.objects.create(code="ADMIN", name="Admin")
        perm = Permission.objects.create(code="user.manage")
        RolePermission.objects.create(role=role, permission=perm)
        with self.assertRaises(IntegrityError):
            RolePermission.objects.create(role=role, permission=perm)


class UserRoleModelTests(TestCase):
    def test_user_role_pair_is_unique(self):
        user = User.objects.create_user(email="a@example.com", password="pw12345")
        role = Role.objects.create(code="SUPPORT", name="Support")
        UserRole.objects.create(user=user, role=role)
        with self.assertRaises(IntegrityError):
            UserRole.objects.create(user=user, role=role)


class SeedRbacCommandTests(TestCase):
    def test_seed_is_idempotent_and_matches_matrix(self):
        call_command("seed_rbac")
        call_command("seed_rbac")

        self.assertEqual(Role.objects.count(), 4)
        self.assertEqual(Permission.objects.count(), 9)

        admin = Role.objects.get(code="ADMIN")
        admin_perms = set(
            RolePermission.objects.filter(role=admin).values_list("permission__code", flat=True)
        )
        self.assertIn("user.manage", admin_perms)
        self.assertIn("audit.view", admin_perms)

        client = Role.objects.get(code="CLIENT")
        client_perms = set(
            RolePermission.objects.filter(role=client).values_list("permission__code", flat=True)
        )
        self.assertEqual(client_perms, {"product.view", "application.view_own", "loan.view_own"})


@override_settings(CACHES=TEST_CACHES)
class AssignRevokeRoleServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_rbac")
        self.user = User.objects.create_user(email="u@example.com", password="pw12345")

    def test_assign_role_creates_link_and_syncs_denormalized_field(self):
        assign_role(self.user, "UNDERWRITER")
        self.user.refresh_from_db()

        self.assertTrue(UserRole.objects.filter(user=self.user, role__code="UNDERWRITER").exists())
        self.assertEqual(self.user.role, "UNDERWRITER")

    def test_assign_role_is_idempotent(self):
        assign_role(self.user, "SUPPORT")
        assign_role(self.user, "SUPPORT")
        self.assertEqual(UserRole.objects.filter(user=self.user, role__code="SUPPORT").count(), 1)

    def test_assign_role_invalidates_permission_cache(self):
        cache.set(f"user_perms:{self.user.id}", {"stale.permission"}, 300)
        assign_role(self.user, "ADMIN")
        self.assertIsNone(cache.get(f"user_perms:{self.user.id}"))

    def test_revoke_role_removes_link_and_invalidates_cache(self):
        assign_role(self.user, "ADMIN")
        cache.set(f"user_perms:{self.user.id}", {"cached"}, 300)

        revoke_role(self.user, "ADMIN")

        self.assertFalse(UserRole.objects.filter(user=self.user, role__code="ADMIN").exists())
        self.assertIsNone(cache.get(f"user_perms:{self.user.id}"))


@override_settings(CACHES=TEST_CACHES)
class UserHasPermissionTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_rbac")

    def test_permission_granted_via_role(self):
        user = User.objects.create_user(email="c@example.com", password="pw12345")
        assign_role(user, "UNDERWRITER")

        self.assertTrue(user_has_permission(user, "application.approve"))
        self.assertFalse(user_has_permission(user, "user.manage"))

    def test_permission_set_is_cached_after_first_lookup(self):
        user = User.objects.create_user(email="d@example.com", password="pw12345")
        assign_role(user, "ADMIN")

        user_has_permission(user, "audit.view")
        cached = cache.get(f"user_perms:{user.id}")

        self.assertIsNotNone(cached)
        self.assertIn("audit.view", cached)

    def test_user_without_role_has_no_permissions(self):
        user = User.objects.create_user(email="e@example.com", password="pw12345")
        self.assertFalse(user_has_permission(user, "product.view"))
