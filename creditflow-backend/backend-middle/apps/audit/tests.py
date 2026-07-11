from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.rbac.services import assign_role
from common.audit import audit_log

from .models import AuditLog

TEST_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class AuditLogModelTests(TestCase):
    def test_str_representation(self):
        entry = AuditLog.objects.create(
            action="loan.disbursed", object_type="Loan", object_id=1, changes={"a": 1}
        )
        self.assertIn("loan.disbursed", str(entry))
        self.assertIn("Loan#1", str(entry))

    def test_actor_defaults_to_null(self):
        entry = AuditLog.objects.create(action="loan.disbursed", object_type="Loan", object_id=1)
        self.assertIsNone(entry.actor)
        self.assertEqual(entry.changes, {})


class AuditLogHelperTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="actor@example.com", password="pw12345")

    def test_creates_entry_with_actor_and_changes(self):
        entry_obj = User.objects.create_user(email="target@example.com", password="pw12345")
        audit_log(
            self.user, "user.role_assigned", entry_obj, changes={"before": "CLIENT", "after": "ADMIN"}
        )
        entry = AuditLog.objects.get(action="user.role_assigned")
        self.assertEqual(entry.actor, self.user)
        self.assertEqual(entry.object_type, "User")
        self.assertEqual(entry.object_id, entry_obj.id)
        self.assertEqual(entry.changes, {"before": "CLIENT", "after": "ADMIN"})
        self.assertIsNone(entry.ip_address)

    def test_none_actor_is_stored_as_null(self):
        target = User.objects.create_user(email="sys-target@example.com", password="pw12345")
        audit_log(None, "application.status_changed", target, changes={"before": "SUBMITTED", "after": "SCORING"})
        entry = AuditLog.objects.get(action="application.status_changed")
        self.assertIsNone(entry.actor)

    def test_extracts_ip_from_x_forwarded_for(self):
        from django.test import RequestFactory

        request = RequestFactory().post("/", HTTP_X_FORWARDED_FOR="203.0.113.5, 10.0.0.1")
        target = User.objects.create_user(email="ip-target@example.com", password="pw12345")
        audit_log(self.user, "user.role_assigned", target, request=request)
        entry = AuditLog.objects.get(action="user.role_assigned")
        self.assertEqual(entry.ip_address, "203.0.113.5")


@override_settings(CACHES=TEST_CACHES)
class AuditLogApiTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_rbac")
        self.admin = User.objects.create_user(email="admin@example.com", password="pw12345")
        assign_role(self.admin, "ADMIN")
        self.client_user = User.objects.create_user(email="client@example.com", password="pw12345")
        assign_role(self.client_user, "CLIENT")
        self.api = APIClient()

        AuditLog.objects.create(
            actor=self.admin, action="loan.disbursed", object_type="Loan", object_id=1
        )
        AuditLog.objects.create(
            actor=None, action="application.status_changed", object_type="CreditApplication", object_id=5
        )

    def test_requires_authentication(self):
        r = self.api.get("/api/v1/admin/audit-log")
        self.assertEqual(r.status_code, 401)

    def test_denies_user_without_audit_view_permission(self):
        self.api.force_authenticate(user=self.client_user)
        r = self.api.get("/api/v1/admin/audit-log")
        self.assertEqual(r.status_code, 403)

    def test_admin_can_list_audit_log(self):
        self.api.force_authenticate(user=self.admin)
        r = self.api.get("/api/v1/admin/audit-log")
        self.assertEqual(r.status_code, 200)
        # setUp's two explicit entries plus the two user.role_assigned entries
        # written by assign_role() itself (Doc 3 §14).
        self.assertEqual(r.data["count"], 4)

    def test_filters_by_action(self):
        self.api.force_authenticate(user=self.admin)
        r = self.api.get("/api/v1/admin/audit-log?action=loan.disbursed")
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(r.data["results"][0]["action"], "loan.disbursed")

    def test_filters_by_object_type(self):
        self.api.force_authenticate(user=self.admin)
        r = self.api.get("/api/v1/admin/audit-log?object_type=Loan")
        self.assertEqual(r.data["count"], 1)
