import pytest
from rest_framework.test import APIClient

from apps.accounts.services import register_user
from apps.products.models import CreditProduct

pytestmark = pytest.mark.django_db


@pytest.fixture
def product(db):
    return CreditProduct.objects.create(
        name="Потребительский",
        slug="consumer",
        min_amount="10000.00",
        max_amount="500000.00",
        interest_rate="18.50",
        min_term_months=3,
        max_term_months=36,
        is_active=True,
    )


def make_authed_client(email, monthly_income=None, birth_date=None):
    user = register_user(email=email, password="StrongPass123")
    profile = user.profile
    profile.monthly_income = monthly_income
    profile.birth_date = birth_date
    profile.save()

    client = APIClient()
    login = client.post("/api/v1/auth/login", {"email": email, "password": "StrongPass123"})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client, user


@pytest.fixture
def approved_client():
    return make_authed_client("approved@b.com", monthly_income="100000.00", birth_date="1990-01-01")


@pytest.fixture
def rejected_client():
    return make_authed_client("rejected@b.com", monthly_income=None, birth_date=None)


def test_create_application_draft(approved_client, product):
    client, _ = approved_client
    r = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12, "purpose": "Ремонт"},
    )
    assert r.status_code == 201
    assert r.data["status"] == "DRAFT"
    assert r.data["product"] == product.id


def test_create_application_missing_product_returns_404(approved_client):
    client, _ = approved_client
    r = client.post(
        "/api/v1/credit-applications",
        {"product": 999999, "amount": "200000.00", "term_months": 12},
    )
    assert r.status_code == 404
    assert r.data["error"]["code"] == "NOT_FOUND"


def test_create_application_inactive_product_returns_400(approved_client, product):
    product.is_active = False
    product.save()
    client, _ = approved_client
    r = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    assert r.status_code == 400


def test_create_application_amount_out_of_range_returns_400(approved_client, product):
    client, _ = approved_client
    r = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "999999999.00", "term_months": 12},
    )
    assert r.status_code == 400
    assert r.data["error"]["code"] == "VALIDATION_ERROR"


def test_list_only_returns_own_applications(approved_client, rejected_client, product):
    client_a, _ = approved_client
    client_b, _ = rejected_client
    client_a.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    r = client_b.get("/api/v1/credit-applications")
    assert r.data["count"] == 0


def test_retrieve_other_users_application_returns_404(approved_client, rejected_client, product):
    client_a, _ = approved_client
    client_b, _ = rejected_client
    created = client_a.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    r = client_b.get(f"/api/v1/credit-applications/{created.data['id']}")
    assert r.status_code == 404


def test_update_draft_application(approved_client, product):
    client, _ = approved_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    r = client.put(
        f"/api/v1/credit-applications/{created.data['id']}",
        {"amount": "250000.00", "term_months": 24, "purpose": "Авто"},
    )
    assert r.status_code == 200
    assert r.data["amount"] == "250000.00"


def test_update_non_draft_returns_409(approved_client, product):
    client, _ = approved_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    app_id = created.data["id"]
    client.post(f"/api/v1/credit-applications/{app_id}/submit")
    r = client.put(
        f"/api/v1/credit-applications/{app_id}",
        {"amount": "250000.00", "term_months": 24, "purpose": "Авто"},
    )
    assert r.status_code == 409
    assert r.data["error"]["code"] == "CONFLICT"


def test_delete_draft_application(approved_client, product):
    client, _ = approved_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    r = client.delete(f"/api/v1/credit-applications/{created.data['id']}")
    assert r.status_code == 204


def test_delete_non_draft_returns_409(approved_client, product):
    client, _ = approved_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    app_id = created.data["id"]
    client.post(f"/api/v1/credit-applications/{app_id}/submit")
    r = client.delete(f"/api/v1/credit-applications/{app_id}")
    assert r.status_code == 409


def test_submit_approves_with_sufficient_income(approved_client, product):
    client, _ = approved_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    app_id = created.data["id"]
    r = client.post(f"/api/v1/credit-applications/{app_id}/submit")
    assert r.status_code == 200
    assert r.data["status"] == "APPROVED"
    assert r.data["monthly_payment"] is not None
    assert r.data["scoring_result"]["decision"] == "APPROVED"


def test_submit_rejects_with_missing_income_data(rejected_client, product):
    client, _ = rejected_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    app_id = created.data["id"]
    r = client.post(f"/api/v1/credit-applications/{app_id}/submit")
    assert r.status_code == 200
    assert r.data["status"] == "REJECTED"


def test_submit_non_draft_returns_409(approved_client, product):
    client, _ = approved_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    app_id = created.data["id"]
    client.post(f"/api/v1/credit-applications/{app_id}/submit")
    r = client.post(f"/api/v1/credit-applications/{app_id}/submit")
    assert r.status_code == 409


def test_search_by_purpose(approved_client, product):
    client, _ = approved_client
    client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12, "purpose": "Ремонт квартиры"},
    )
    client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "50000.00", "term_months": 6, "purpose": "Свадьба"},
    )
    r = client.get("/api/v1/credit-applications?search=Ремонт")
    assert r.data["count"] == 1


def test_filter_by_status(approved_client, product):
    client, _ = approved_client
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    client.post(f"/api/v1/credit-applications/{created.data['id']}/submit")
    client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "50000.00", "term_months": 6},
    )
    r = client.get("/api/v1/credit-applications?status=DRAFT")
    assert r.data["count"] == 1
