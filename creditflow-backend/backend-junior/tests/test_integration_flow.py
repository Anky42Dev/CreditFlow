"""Full happy-path integration test (DOC 0 §2.1 UJ-1): register -> login ->
fill profile -> browse products -> create application -> submit -> see result.
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Profile, User
from apps.products.models import CreditProduct

pytestmark = pytest.mark.django_db


def test_full_credit_journey_happy_path():
    client = APIClient()

    # 1. Guest registers
    r = client.post(
        "/api/v1/auth/register",
        {"email": "journey@test.com", "password": "StrongPass123"},
    )
    assert r.status_code == 201
    assert r.data["role"] == "CLIENT"
    assert User.objects.filter(email="journey@test.com").exists()
    assert Profile.objects.filter(user__email="journey@test.com").exists()

    # 2. Logs in, receives JWT pair
    r = client.post(
        "/api/v1/auth/login",
        {"email": "journey@test.com", "password": "StrongPass123"},
    )
    assert r.status_code == 200
    access, refresh = r.data["access"], r.data["refresh"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    # 3. Confirms identity via /auth/me
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.data["email"] == "journey@test.com"

    # 4. Fills profile (income high enough to guarantee approval)
    r = client.put(
        "/api/v1/profile",
        {
            "first_name": "Иван",
            "last_name": "Петров",
            "birth_date": "1990-01-01",
            "phone": "+996700123456",
            "monthly_income": "150000.00",
        },
        format="json",
    )
    assert r.status_code == 200

    # 5. Seeds and browses the public product catalog
    product = CreditProduct.objects.create(
        name="Потребительский",
        slug="consumer",
        min_amount="10000.00",
        max_amount="500000.00",
        interest_rate="18.50",
        min_term_months=3,
        max_term_months=36,
        is_active=True,
    )
    r = client.get("/api/v1/credit-products")
    assert r.status_code == 200
    assert r.data["count"] == 1
    assert r.data["results"][0]["id"] == product.id

    # 6. Creates a DRAFT application
    r = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12, "purpose": "Ремонт"},
    )
    assert r.status_code == 201
    application_id = r.data["id"]
    assert r.data["status"] == "DRAFT"

    # 7. Sees the DRAFT application in their own list
    r = client.get("/api/v1/credit-applications")
    assert r.data["count"] == 1

    # 8. Submits -> synchronous scoring runs -> APPROVED with computed schedule seed
    r = client.post(f"/api/v1/credit-applications/{application_id}/submit")
    assert r.status_code == 200
    assert r.data["status"] == "APPROVED"
    assert r.data["monthly_payment"] is not None
    assert r.data["scoring_result"]["decision"] == "APPROVED"
    assert r.data["scoring_result"]["score"] >= 600

    # 9. Detail view reflects the final state, including nested scoring result
    r = client.get(f"/api/v1/credit-applications/{application_id}")
    assert r.status_code == 200
    assert r.data["status"] == "APPROVED"
    assert r.data["scoring_result"] is not None

    # 10. An expired/garbage access token no longer works, but refresh restores access
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401

    r = client.post("/api/v1/auth/refresh", {"refresh": refresh})
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200


def test_full_journey_rejects_when_income_data_is_missing():
    client = APIClient()
    client.post(
        "/api/v1/auth/register",
        {"email": "poor@test.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/api/v1/auth/login", {"email": "poor@test.com", "password": "StrongPass123"}
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    product = CreditProduct.objects.create(
        name="Экспресс",
        slug="express",
        min_amount="5000.00",
        max_amount="100000.00",
        interest_rate="24.90",
        min_term_months=1,
        max_term_months=12,
        is_active=True,
    )
    # profile left empty: no birth_date, no monthly_income
    created = client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "50000.00", "term_months": 6},
    )
    r = client.post(f"/api/v1/credit-applications/{created.data['id']}/submit")
    assert r.status_code == 200
    assert r.data["status"] == "REJECTED"
