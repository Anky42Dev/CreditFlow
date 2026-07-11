"""Traceability tests for DOC 1 §14 Acceptance Criteria (AC-1..AC-9)."""
from datetime import timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Profile, User
from apps.accounts.services import register_user
from apps.products.models import CreditProduct

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


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


def login(api_client, email, password="StrongPass123"):
    r = api_client.post("/api/v1/auth/login", {"email": email, "password": password})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return r.data


def test_AC1_new_email_registers_user_and_profile_with_client_role(api_client):
    r = api_client.post(
        "/api/v1/auth/register", {"email": "ac1@test.com", "password": "StrongPass123"}
    )
    assert r.status_code == 201
    user = User.objects.get(email="ac1@test.com")
    assert user.role == "CLIENT"
    assert Profile.objects.filter(user=user).exists()


def test_AC2_existing_email_returns_409_email_taken(api_client):
    register_user(email="ac2@test.com", password="StrongPass123")
    r = api_client.post(
        "/api/v1/auth/register", {"email": "ac2@test.com", "password": "StrongPass123"}
    )
    assert r.status_code == 409
    assert r.data["error"]["code"] == "EMAIL_TAKEN"


def test_AC3_valid_credentials_login_returns_access_and_refresh(api_client):
    register_user(email="ac3@test.com", password="StrongPass123")
    r = api_client.post(
        "/api/v1/auth/login", {"email": "ac3@test.com", "password": "StrongPass123"}
    )
    assert r.status_code == 200
    assert "access" in r.data and "refresh" in r.data


def test_AC4_expired_access_token_returns_401_token_expired(api_client):
    user = register_user(email="ac4@test.com", password="StrongPass123")
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=timedelta(seconds=-1))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    r = api_client.get("/api/v1/profile")
    assert r.status_code == 401
    assert r.data["error"]["code"] == "TOKEN_EXPIRED"


def test_AC5_valid_refresh_returns_new_access(api_client):
    register_user(email="ac5@test.com", password="StrongPass123")
    tokens = login(api_client, "ac5@test.com")
    r = api_client.post("/api/v1/auth/refresh", {"refresh": tokens["refresh"]})
    assert r.status_code == 200
    assert "access" in r.data


def test_AC6_draft_application_in_range_submits_to_approved_or_rejected(api_client, product):
    register_user(email="ac6@test.com", password="StrongPass123")
    login(api_client, "ac6@test.com")
    created = api_client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    assert created.data["status"] == "DRAFT"
    r = api_client.post(f"/api/v1/credit-applications/{created.data['id']}/submit")
    assert r.status_code == 200
    assert r.data["status"] in ("APPROVED", "REJECTED")


def test_AC7_non_draft_application_submit_returns_409_conflict(api_client, product):
    register_user(email="ac7@test.com", password="StrongPass123")
    login(api_client, "ac7@test.com")
    created = api_client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )
    app_id = created.data["id"]
    api_client.post(f"/api/v1/credit-applications/{app_id}/submit")
    r = api_client.post(f"/api/v1/credit-applications/{app_id}/submit")
    assert r.status_code == 409
    assert r.data["error"]["code"] == "CONFLICT"


def test_AC8_foreign_application_returns_404(api_client, product):
    owner = register_user(email="ac8-owner@test.com", password="StrongPass123")
    register_user(email="ac8-other@test.com", password="StrongPass123")

    owner_client = APIClient()
    login(owner_client, "ac8-owner@test.com")
    created = owner_client.post(
        "/api/v1/credit-applications",
        {"product": product.id, "amount": "200000.00", "term_months": 12},
    )

    login(api_client, "ac8-other@test.com")
    r = api_client.get(f"/api/v1/credit-applications/{created.data['id']}")
    assert r.status_code == 404


def test_AC9_avatar_over_2mb_returns_400(api_client):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image
    import io

    register_user(email="ac9@test.com", password="StrongPass123")
    login(api_client, "ac9@test.com")

    image = Image.new("RGB", (500, 500), color="blue")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    content = buffer.getvalue() + b"0" * (3 * 1024 * 1024)
    file = SimpleUploadedFile("big.jpg", content, content_type="image/jpeg")

    r = api_client.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
    assert r.status_code == 400
