from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.rbac.services import assign_role
from common.audit import audit_log

from .models import AuditLog
from .services import create_future_partitions

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
class AuditLogApiTests(TransactionTestCase):
    """TransactionTestCase, not TestCase: AuditLogViewSet.get_queryset()
    reads via the 'replica' alias (DOC 5 §14) — a genuinely separate
    connection from 'default', even though DATABASES['replica']['TEST']
    mirrors the same physical test DB (see config/db_router.py's docstring).
    TestCase wraps each alias in its own uncommitted atomic() block, so
    writes made here in setUp() via 'default' would be invisible to a read
    via 'replica' unless they're actually committed — which is what
    TransactionTestCase does (and is the honest simulation of production
    replica behavior anyway)."""

    databases = {"default", "replica"}

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
        # written by assign_role() itself (Doc 3 §14). Cursor pagination
        # (DOC 5 §14) has no "count" field — check the page instead.
        self.assertEqual(len(r.data["results"]), 4)
        self.assertIsNone(r.data["previous"])

    def test_filters_by_action(self):
        self.api.force_authenticate(user=self.admin)
        r = self.api.get("/api/v1/admin/audit-log?action=loan.disbursed")
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data["results"][0]["action"], "loan.disbursed")

    def test_filters_by_object_type(self):
        self.api.force_authenticate(user=self.admin)
        r = self.api.get("/api/v1/admin/audit-log?object_type=Loan")
        self.assertEqual(len(r.data["results"]), 1)

    def test_cursor_pagination_next_page_has_no_overlap_or_gap(self):
        """DOC 5 §14: keyset pagination — walking `next` links must visit
        every extra entry exactly once, in the declared (newest-first) order."""
        for i in range(25):
            AuditLog.objects.create(
                actor=self.admin, action="bulk.entry", object_type="Bulk", object_id=i
            )
        self.api.force_authenticate(user=self.admin)

        first = self.api.get("/api/v1/admin/audit-log?action=bulk.entry")
        self.assertEqual(len(first.data["results"]), 20)
        self.assertIsNotNone(first.data["next"])

        second = self.api.get(first.data["next"])
        self.assertEqual(len(second.data["results"]), 5)

        seen_ids = [row["id"] for row in first.data["results"] + second.data["results"]]
        self.assertEqual(len(seen_ids), len(set(seen_ids)))  # no duplicates
        self.assertEqual(seen_ids, sorted(seen_ids, reverse=True))  # newest-first, unbroken

    def test_admin_can_retrieve_single_entry_by_id(self):
        """DOC 5 §14: AuditLog's PK is now composite (id, created_at) — the
        detail route must look up by `id` (lookup_field override in
        AuditLogViewSet), not DRF's default `pk` filter, which would break
        against a composite PK."""
        entry = AuditLog.objects.create(
            actor=self.admin, action="loan.disbursed", object_type="Loan", object_id=42
        )
        self.api.force_authenticate(user=self.admin)
        r = self.api.get(f"/api/v1/admin/audit-log/{entry.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], entry.id)
        self.assertEqual(r.data["object_id"], 42)


class CreateFuturePartitionsTests(TestCase):
    """DOC 5 §14, Roadmap Этап 5 п.14: apps.audit.services.create_future_partitions
    (management command + Celery Beat task both call this)."""

    def _partition_names(self, table):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT inhrelid::regclass::text FROM pg_inherits "
                "WHERE inhparent = %s::regclass",
                [table],
            )
            return {row[0] for row in cursor.fetchall()}

    def test_creates_months_ahead_partitions_for_both_tables(self):
        create_future_partitions(months_ahead=5)

        audit_partitions = self._partition_names("audit_logs")
        transaction_partitions = self._partition_names("transactions")
        # +1 because the loop is inclusive of the current month (0..N).
        self.assertGreaterEqual(len(audit_partitions), 6)
        self.assertGreaterEqual(len(transaction_partitions), 6)

    def test_is_idempotent(self):
        create_future_partitions(months_ahead=2)
        before = self._partition_names("audit_logs")
        create_future_partitions(months_ahead=2)
        after = self._partition_names("audit_logs")
        self.assertEqual(before, after)

    def test_rejects_negative_months_ahead(self):
        with self.assertRaises(ValueError):
            create_future_partitions(months_ahead=-1)

    def test_management_command_runs(self):
        call_command("create_future_partitions", "--months-ahead", "1")
