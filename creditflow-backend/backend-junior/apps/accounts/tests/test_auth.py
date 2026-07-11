import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_register_creates_client_user(api_client):
    r = api_client.post(
        "/api/v1/auth/register",
        {"email": "a@b.com", "password": "StrongPass123"},
    )
    assert r.status_code == 201
    assert r.data["email"] == "a@b.com"
    assert r.data["role"] == "CLIENT"
    assert User.objects.get(email="a@b.com").check_password("StrongPass123")


def test_register_duplicate_email_returns_409(api_client):
    User.objects.create_user(email="a@b.com", password="StrongPass123")
    r = api_client.post(
        "/api/v1/auth/register",
        {"email": "a@b.com", "password": "StrongPass123"},
    )
    assert r.status_code == 409
    assert r.data["error"]["code"] == "EMAIL_TAKEN"


def test_register_weak_password_returns_400(api_client):
    r = api_client.post(
        "/api/v1/auth/register",
        {"email": "a@b.com", "password": "12345678"},
    )
    assert r.status_code == 400
    assert r.data["error"]["code"] == "VALIDATION_ERROR"


def test_login_success_returns_access_and_refresh(api_client):
    User.objects.create_user(email="a@b.com", password="StrongPass123")
    r = api_client.post(
        "/api/v1/auth/login",
        {"email": "a@b.com", "password": "StrongPass123"},
    )
    assert r.status_code == 200
    assert "access" in r.data and "refresh" in r.data


def test_login_invalid_credentials_returns_401(api_client):
    User.objects.create_user(email="a@b.com", password="StrongPass123")
    r = api_client.post(
        "/api/v1/auth/login",
        {"email": "a@b.com", "password": "WrongPass123"},
    )
    assert r.status_code == 401
    assert r.data["error"]["code"] == "AUTHENTICATION_FAILED"


def test_refresh_returns_new_access_token(api_client):
    User.objects.create_user(email="a@b.com", password="StrongPass123")
    login = api_client.post(
        "/api/v1/auth/login",
        {"email": "a@b.com", "password": "StrongPass123"},
    )
    r = api_client.post("/api/v1/auth/refresh", {"refresh": login.data["refresh"]})
    assert r.status_code == 200
    assert "access" in r.data


def test_refresh_invalid_token_returns_401_token_expired(api_client):
    r = api_client.post("/api/v1/auth/refresh", {"refresh": "not-a-real-token"})
    assert r.status_code == 401
    assert r.data["error"]["code"] == "TOKEN_EXPIRED"


def test_me_authenticated_returns_current_user(api_client):
    User.objects.create_user(email="a@b.com", password="StrongPass123")
    login = api_client.post(
        "/api/v1/auth/login",
        {"email": "a@b.com", "password": "StrongPass123"},
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    r = api_client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.data["email"] == "a@b.com"


def test_me_unauthenticated_returns_401(api_client):
    r = api_client.get("/api/v1/auth/me")
    assert r.status_code == 401
