from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User

from .models import CreditProduct


class CreditProductViewSetTests(TestCase):
    def setUp(self):
        self.active = CreditProduct.objects.create(
            name="Active", slug="active", min_amount=Decimal("1000"), max_amount=Decimal("50000"),
            interest_rate=Decimal("10.00"), min_term_months=3, max_term_months=12, is_active=True,
        )
        self.inactive = CreditProduct.objects.create(
            name="Inactive", slug="inactive", min_amount=Decimal("1000"), max_amount=Decimal("50000"),
            interest_rate=Decimal("10.00"), min_term_months=3, max_term_months=12, is_active=False,
        )
        self.client_ = APIClient()

    def test_anonymous_sees_only_active_products(self):
        r = self.client_.get("/api/v1/credit-products")
        ids = [item["id"] for item in r.data["results"]]
        self.assertIn(self.active.id, ids)
        self.assertNotIn(self.inactive.id, ids)

    def test_staff_sees_inactive_products_too(self):
        staff = User.objects.create_user(email="staff@example.com", password="pw12345", is_staff=True)
        self.client_.force_authenticate(user=staff)
        r = self.client_.get("/api/v1/credit-products")
        ids = [item["id"] for item in r.data["results"]]
        self.assertIn(self.inactive.id, ids)
