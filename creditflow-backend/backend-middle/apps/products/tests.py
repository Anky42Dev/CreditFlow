from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User

from .models import CreditProduct
from .services import (
    ACTIVE_PRODUCTS_CACHE_KEY,
    PRODUCT_DETAIL_CACHE_KEY,
    get_active_products,
    get_product_detail,
    invalidate_product_cache,
)

TEST_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class CreditProductViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
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


@override_settings(CACHES=TEST_CACHES)
class ProductCacheServiceTests(TestCase):
    """Doc 3 §8: products:active / product:{id}, TTL 600s, invalidated on write."""

    def setUp(self):
        cache.clear()
        self.active = CreditProduct.objects.create(
            name="Active", slug="active", min_amount=Decimal("1000"), max_amount=Decimal("50000"),
            interest_rate=Decimal("10.00"), min_term_months=3, max_term_months=12, is_active=True,
        )

    def test_get_active_products_populates_cache(self):
        self.assertIsNone(cache.get(ACTIVE_PRODUCTS_CACHE_KEY))
        data = get_active_products()
        self.assertEqual(len(data), 1)
        self.assertIsNotNone(cache.get(ACTIVE_PRODUCTS_CACHE_KEY))

    def test_get_active_products_excludes_inactive_and_uses_cache_on_second_call(self):
        get_active_products()
        # Mutate the DB without invalidating — the cached copy should be served.
        CreditProduct.objects.create(
            name="Extra", slug="extra", min_amount=Decimal("1000"), max_amount=Decimal("50000"),
            interest_rate=Decimal("10.00"), min_term_months=3, max_term_months=12, is_active=True,
        )
        data = get_active_products()
        self.assertEqual(len(data), 1)

    def test_get_product_detail_populates_and_reads_cache(self):
        key = PRODUCT_DETAIL_CACHE_KEY.format(id=self.active.id)
        self.assertIsNone(cache.get(key))
        data = get_product_detail(self.active.id)
        self.assertEqual(data["id"], self.active.id)
        self.assertIsNotNone(cache.get(key))

    def test_get_product_detail_returns_none_for_missing_product(self):
        self.assertIsNone(get_product_detail(999999))

    def test_invalidate_product_cache_clears_both_keys(self):
        get_active_products()
        get_product_detail(self.active.id)
        invalidate_product_cache(self.active.id)
        self.assertIsNone(cache.get(ACTIVE_PRODUCTS_CACHE_KEY))
        self.assertIsNone(cache.get(PRODUCT_DETAIL_CACHE_KEY.format(id=self.active.id)))

    def test_api_list_is_served_from_cache_for_anonymous_unfiltered_request(self):
        client_ = APIClient()
        client_.get("/api/v1/credit-products")
        self.assertIsNotNone(cache.get(ACTIVE_PRODUCTS_CACHE_KEY))

    def test_api_list_with_filters_bypasses_cache(self):
        client_ = APIClient()
        client_.get("/api/v1/credit-products?is_active=true")
        self.assertIsNone(cache.get(ACTIVE_PRODUCTS_CACHE_KEY))
