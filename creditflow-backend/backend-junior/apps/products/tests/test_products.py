import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.products.models import CreditProduct

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def active_product(db):
    return CreditProduct.objects.create(
        name="Потребительский",
        slug="consumer",
        description="Кредит на любые цели",
        min_amount="10000.00",
        max_amount="500000.00",
        interest_rate="18.50",
        min_term_months=3,
        max_term_months=36,
        is_active=True,
    )


@pytest.fixture
def inactive_product(db):
    return CreditProduct.objects.create(
        name="Архивный",
        slug="archived",
        description="Снят с продажи",
        min_amount="10000.00",
        max_amount="300000.00",
        interest_rate="22.00",
        min_term_months=3,
        max_term_months=24,
        is_active=False,
    )


def test_list_products_is_public(api_client, active_product):
    r = api_client.get("/api/v1/credit-products")
    assert r.status_code == 200
    assert r.data["count"] == 1


def test_list_hides_inactive_for_anonymous(api_client, active_product, inactive_product):
    r = api_client.get("/api/v1/credit-products")
    slugs = [p["slug"] for p in r.data["results"]]
    assert "archived" not in slugs
    assert "consumer" in slugs


def test_list_shows_inactive_for_staff(api_client, active_product, inactive_product):
    staff = User.objects.create_user(email="staff@b.com", password="StrongPass123", is_staff=True)
    api_client.force_authenticate(user=staff)
    r = api_client.get("/api/v1/credit-products")
    assert r.data["count"] == 2


def test_retrieve_product_detail(api_client, active_product):
    r = api_client.get(f"/api/v1/credit-products/{active_product.id}")
    assert r.status_code == 200
    assert r.data["slug"] == "consumer"


def test_retrieve_missing_product_returns_404(api_client):
    r = api_client.get("/api/v1/credit-products/9999")
    assert r.status_code == 404
    assert r.data["error"]["code"] == "NOT_FOUND"


def test_search_by_name(api_client, active_product):
    r = api_client.get("/api/v1/credit-products?search=Потреб")
    assert r.data["count"] == 1


def test_filter_min_amount(api_client, active_product):
    r = api_client.get("/api/v1/credit-products?min_amount=20000")
    assert r.data["count"] == 0
    r = api_client.get("/api/v1/credit-products?min_amount=5000")
    assert r.data["count"] == 1


def test_ordering_by_interest_rate(api_client):
    CreditProduct.objects.create(
        name="A", slug="a", min_amount=1000, max_amount=5000,
        interest_rate="10.00", min_term_months=1, max_term_months=12, is_active=True,
    )
    CreditProduct.objects.create(
        name="B", slug="b", min_amount=1000, max_amount=5000,
        interest_rate="20.00", min_term_months=1, max_term_months=12, is_active=True,
    )
    r = api_client.get("/api/v1/credit-products?ordering=interest_rate")
    assert [p["slug"] for p in r.data["results"]] == ["a", "b"]


def test_write_methods_not_allowed(api_client, active_product):
    r = api_client.post("/api/v1/credit-products", {"name": "X"})
    assert r.status_code == 405


def test_max_amount_less_than_min_amount_violates_constraint(db):
    with pytest.raises(IntegrityError):
        CreditProduct.objects.create(
            name="Bad", slug="bad", min_amount=5000, max_amount=1000,
            interest_rate="10.00", min_term_months=1, max_term_months=12,
        )
