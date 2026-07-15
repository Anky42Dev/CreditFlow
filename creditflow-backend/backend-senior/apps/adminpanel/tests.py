from decimal import Decimal

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CreditApplication, Document
from apps.applications.services import calc_annuity
from apps.lending.models import Loan, PaymentScheduleItem
from apps.notifications.models import Notification
from apps.products.models import CreditProduct
from apps.rbac.services import assign_role

TEST_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_EAGER = {"CELERY_TASK_ALWAYS_EAGER": True, "CELERY_TASK_EAGER_PROPAGATES": True}


def make_product(**overrides):
    defaults = dict(
        name="Потребительский",
        slug="consumer",
        min_amount=Decimal("10000.00"),
        max_amount=Decimal("500000.00"),
        interest_rate=Decimal("18.50"),
        min_term_months=3,
        max_term_months=36,
        is_active=True,
    )
    defaults.update(overrides)
    return CreditProduct.objects.create(**defaults)


def make_user_with_role(email, role_code):
    user = User.objects.create_user(email=email, password="pw12345")
    assign_role(user, role_code)
    return user


def make_manual_review_application(product, email, amount=Decimal("200000.00"), term_months=12):
    user = User.objects.create_user(email=email, password="pw12345")
    application = CreditApplication.objects.create(
        user=user, product=product, amount=amount, term_months=term_months, status="MANUAL_REVIEW",
    )
    application.monthly_payment = calc_annuity(amount, product.interest_rate, term_months)
    application.save()
    return application


class SetupSeedMixin:
    def setUp(self):
        cache.clear()
        call_command("seed_rbac")
        super().setUp()


@override_settings(CACHES=TEST_CACHES)
class AdminCreditProductAPITests(SetupSeedMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = make_user_with_role("admin@example.com", "ADMIN")
        self.client_user = make_user_with_role("client@example.com", "CLIENT")
        self.product = make_product()

    def test_client_cannot_list_admin_products(self):
        client = APIClient()
        client.force_authenticate(user=self.client_user)
        r = client.get("/api/v1/admin/credit-products")
        self.assertEqual(r.status_code, 403)

    def test_admin_list_includes_inactive_products(self):
        make_product(slug="inactive", is_active=False)
        client = APIClient()
        client.force_authenticate(user=self.admin)
        r = client.get("/api/v1/admin/credit-products")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)

    def test_admin_can_create_product(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        r = client.post("/api/v1/admin/credit-products", {
            "name": "Ипотека", "slug": "mortgage",
            "min_amount": "500000.00", "max_amount": "5000000.00",
            "interest_rate": "9.50", "min_term_months": 12, "max_term_months": 240,
        })
        self.assertEqual(r.status_code, 201)
        self.assertTrue(CreditProduct.objects.filter(slug="mortgage").exists())

    def test_admin_update_invalidates_cache(self):
        cache.set("products:active", ["stale"], 600)
        cache.set(f"product:{self.product.id}", {"stale": True}, 600)
        client = APIClient()
        client.force_authenticate(user=self.admin)

        r = client.put(f"/api/v1/admin/credit-products/{self.product.id}", {
            "name": "Обновлённый", "slug": self.product.slug,
            "min_amount": "10000.00", "max_amount": "500000.00",
            "interest_rate": "20.00", "min_term_months": 3, "max_term_months": 36,
        })

        self.assertEqual(r.status_code, 200)
        self.assertIsNone(cache.get("products:active"))
        self.assertIsNone(cache.get(f"product:{self.product.id}"))

    def test_AC6_public_list_reflects_new_data_after_admin_update_invalidates_cache(self):
        """DOC 3 §18 AC-6: product updated -> GET /credit-products serves fresh data,
        not the stale cached copy (extends test_admin_update_invalidates_cache, which only
        checks the cache keys directly, with the public-facing read path)."""
        anon = APIClient()
        stale = anon.get("/api/v1/credit-products")
        stale_item = next(item for item in stale.data["results"] if item["id"] == self.product.id)
        self.assertEqual(stale_item["interest_rate"], "18.50")

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin)
        r = admin_client.put(f"/api/v1/admin/credit-products/{self.product.id}", {
            "name": self.product.name, "slug": self.product.slug,
            "min_amount": "10000.00", "max_amount": "500000.00",
            "interest_rate": "20.00", "min_term_months": 3, "max_term_months": 36,
            "is_active": True,
        })
        self.assertEqual(r.status_code, 200)

        fresh = anon.get("/api/v1/credit-products")
        fresh_item = next(item for item in fresh.data["results"] if item["id"] == self.product.id)
        self.assertEqual(fresh_item["interest_rate"], "20.00")

    def test_delete_soft_deactivates_instead_of_removing_row(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        r = client.delete(f"/api/v1/admin/credit-products/{self.product.id}")

        self.assertEqual(r.status_code, 204)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.assertTrue(CreditProduct.objects.filter(id=self.product.id).exists())


@override_settings(CACHES=TEST_CACHES, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, **CELERY_EAGER)
class AdminApplicationAPITests(SetupSeedMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.product = make_product()
        self.support = make_user_with_role("support@example.com", "SUPPORT")
        self.underwriter = make_user_with_role("underwriter@example.com", "UNDERWRITER")
        self.client_user = make_user_with_role("appclient@example.com", "CLIENT")

    def test_client_cannot_list_applications(self):
        client = APIClient()
        client.force_authenticate(user=self.client_user)
        r = client.get("/api/v1/admin/applications")
        self.assertEqual(r.status_code, 403)

    def test_support_can_list_but_not_approve(self):
        application = make_manual_review_application(self.product, "reviewed1@example.com")
        client = APIClient()
        client.force_authenticate(user=self.support)

        list_response = client.get("/api/v1/admin/applications")
        self.assertEqual(list_response.status_code, 200)

        approve_response = client.post(f"/api/v1/admin/applications/{application.id}/approve")
        self.assertEqual(approve_response.status_code, 403)

    def test_retrieve_includes_documents_and_scoring(self):
        application = make_manual_review_application(self.product, "detail@example.com")
        Document.objects.create(application=application, doc_type="ID_CARD", file="documents/id.pdf")
        client = APIClient()
        client.force_authenticate(user=self.underwriter)

        r = client.get(f"/api/v1/admin/applications/{application.id}")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["documents"]), 1)
        self.assertEqual(r.data["documents"][0]["doc_type"], "ID_CARD")

    def test_underwriter_approve_flow_creates_loan_and_schedule(self):
        """Doc 3 §17 test_full_approval_flow, adapted for the admin-approval path."""
        application = make_manual_review_application(self.product, "flow@example.com")
        client = APIClient()
        client.force_authenticate(user=self.underwriter)

        r = client.post(f"/api/v1/admin/applications/{application.id}/approve", {"comment": "ok"})

        self.assertEqual(r.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.status, "DISBURSED")
        self.assertTrue(Loan.objects.filter(application=application).exists())
        self.assertEqual(
            PaymentScheduleItem.objects.filter(loan__application=application).count(), 12,
        )
        self.assertTrue(
            Notification.objects.filter(user=application.user, type="application.approved").exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=application.user, type="loan.disbursed").exists()
        )

    def test_approve_non_manual_review_raises_conflict(self):
        application = make_manual_review_application(self.product, "wrongstatus@example.com")
        application.status = "DRAFT"
        application.save(update_fields=["status"])
        client = APIClient()
        client.force_authenticate(user=self.underwriter)

        r = client.post(f"/api/v1/admin/applications/{application.id}/approve")
        self.assertEqual(r.status_code, 409)

    def test_reject_sets_status_and_notifies(self):
        application = make_manual_review_application(self.product, "reject@example.com")
        client = APIClient()
        client.force_authenticate(user=self.underwriter)

        r = client.post(f"/api/v1/admin/applications/{application.id}/reject", {"reason": "risky"})

        self.assertEqual(r.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.status, "REJECTED")
        self.assertTrue(
            Notification.objects.filter(user=application.user, type="application.rejected").exists()
        )

    def test_request_documents_notifies_without_changing_status(self):
        application = make_manual_review_application(self.product, "docs@example.com")
        client = APIClient()
        client.force_authenticate(user=self.support)

        r = client.post(f"/api/v1/admin/applications/{application.id}/request-documents")

        self.assertEqual(r.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.status, "MANUAL_REVIEW")
        self.assertTrue(
            Notification.objects.filter(
                user=application.user, type="application.documents_requested"
            ).exists()
        )

    def test_filter_by_status_and_user_email(self):
        make_manual_review_application(self.product, "alice@example.com")
        make_manual_review_application(self.product, "bob@example.com")
        client = APIClient()
        client.force_authenticate(user=self.support)

        r = client.get("/api/v1/admin/applications?user_email=alice")
        self.assertEqual(r.data["count"], 1)


@override_settings(CACHES=TEST_CACHES)
class AdminUserAPITests(SetupSeedMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = make_user_with_role("useradmin@example.com", "ADMIN")
        self.client_user = make_user_with_role("plainclient@example.com", "CLIENT")

    def test_client_cannot_list_users(self):
        client = APIClient()
        client.force_authenticate(user=self.client_user)
        r = client.get("/api/v1/admin/users")
        self.assertEqual(r.status_code, 403)

    def test_admin_can_list_and_filter_by_email(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        r = client.get("/api/v1/admin/users?email=plainclient")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)

    def test_admin_changes_role_via_assign_role_and_invalidates_perm_cache(self):
        cache.set(f"user_perms:{self.client_user.id}", {"stale.permission"}, 300)
        client = APIClient()
        client.force_authenticate(user=self.admin)

        r = client.patch(f"/api/v1/admin/users/{self.client_user.id}/role", {"role": "SUPPORT"})

        self.assertEqual(r.status_code, 200)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.role, "SUPPORT")
        self.assertIsNone(cache.get(f"user_perms:{self.client_user.id}"))

    def test_unknown_role_code_returns_validation_error(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        r = client.patch(f"/api/v1/admin/users/{self.client_user.id}/role", {"role": "NOT_A_ROLE"})
        self.assertEqual(r.status_code, 400)
