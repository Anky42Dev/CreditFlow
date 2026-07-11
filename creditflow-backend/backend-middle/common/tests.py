from types import SimpleNamespace

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.rbac.services import assign_role
from .permissions import HasPermission

TEST_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class FakeAnonymousUser:
    is_authenticated = False


@override_settings(CACHES=TEST_CACHES)
class HasPermissionTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_rbac")
        self.permission = HasPermission()

    def test_denies_unauthenticated_user(self):
        request = SimpleNamespace(user=FakeAnonymousUser())
        view = SimpleNamespace(required_permission="product.view")
        self.assertFalse(self.permission.has_permission(request, view))

    def test_allows_authenticated_user_when_no_permission_required(self):
        user = User.objects.create_user(email="f@example.com", password="pw12345")
        request = SimpleNamespace(user=user)
        view = SimpleNamespace()
        self.assertTrue(self.permission.has_permission(request, view))

    def test_denies_user_missing_required_permission(self):
        user = User.objects.create_user(email="g@example.com", password="pw12345")
        assign_role(user, "CLIENT")
        request = SimpleNamespace(user=user)
        view = SimpleNamespace(required_permission="user.manage")
        self.assertFalse(self.permission.has_permission(request, view))

    def test_allows_user_with_required_permission(self):
        user = User.objects.create_user(email="h@example.com", password="pw12345")
        assign_role(user, "ADMIN")
        request = SimpleNamespace(user=user)
        view = SimpleNamespace(required_permission="user.manage")
        self.assertTrue(self.permission.has_permission(request, view))
