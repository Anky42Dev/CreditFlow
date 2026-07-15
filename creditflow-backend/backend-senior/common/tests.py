from types import SimpleNamespace

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from apps.accounts.models import User
from apps.rbac.services import assign_role

from .logging import mask_pii
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


class RequestContextMiddlewareTests(TestCase):
    """DOC 5 §12.2/§12.3: common.middleware.RequestContextMiddleware."""

    def test_generates_request_and_trace_ids(self):
        response = Client().get("/health/live")
        self.assertIn("X-Request-Id", response.headers)
        self.assertIn("X-Trace-Id", response.headers)

    def test_echoes_an_inbound_trace_id_unchanged(self):
        response = Client().get("/health/live", HTTP_X_TRACE_ID="fixed-trace-id")
        self.assertEqual(response.headers["X-Trace-Id"], "fixed-trace-id")

    def test_generates_a_fresh_trace_id_when_none_is_supplied(self):
        first = Client().get("/health/live").headers["X-Trace-Id"]
        second = Client().get("/health/live").headers["X-Trace-Id"]
        self.assertNotEqual(first, second)


class PrometheusMetricsMiddlewareTests(TestCase):
    """DOC 5 §12.1: common.middleware.PrometheusMetricsMiddleware + /metrics."""

    def test_metrics_endpoint_exposes_http_request_duration(self):
        Client().get("/health/live")
        response = Client().get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cf_http_request_duration_seconds", response.content)


class MaskPiiTests(TestCase):
    """DOC 5 §12.2: PII redaction in the structlog processor chain."""

    def test_masks_known_sensitive_keys(self):
        event = mask_pii(None, "info", {"email": "a@b.com", "password": "secret", "foo": "bar"})
        self.assertEqual(event["email"], "***")
        self.assertEqual(event["password"], "***")
        self.assertEqual(event["foo"], "bar")
