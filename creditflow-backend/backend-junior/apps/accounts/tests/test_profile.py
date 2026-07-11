import io

import pytest
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import register_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def authed_client():
    user = register_user(email="a@b.com", password="StrongPass123")
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login", {"email": "a@b.com", "password": "StrongPass123"}
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client, user


def make_image_file(fmt="PNG", content_type="image/png", size_bytes=None):
    image = Image.new("RGB", (500, 500), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    content = buffer.getvalue()
    if size_bytes:
        content += b"0" * max(0, size_bytes - len(content))
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile("avatar." + fmt.lower(), content, content_type=content_type)


def test_register_creates_empty_profile():
    user = register_user(email="a@b.com", password="StrongPass123")
    assert user.profile is not None
    assert user.profile.first_name == ""


def test_get_profile_requires_auth():
    client = APIClient()
    r = client.get("/api/v1/profile")
    assert r.status_code == 401


def test_get_profile_returns_own_profile(authed_client):
    client, user = authed_client
    r = client.get("/api/v1/profile")
    assert r.status_code == 200
    assert r.data["first_name"] == ""


def test_put_profile_updates_fields(authed_client):
    client, user = authed_client
    r = client.put(
        "/api/v1/profile",
        {
            "first_name": "Иван",
            "last_name": "Петров",
            "birth_date": "1995-04-12",
            "phone": "+996700123456",
            "monthly_income": "80000.00",
        },
        format="json",
    )
    assert r.status_code == 200
    assert r.data["first_name"] == "Иван"
    assert r.data["monthly_income"] == "80000.00"


def test_put_profile_underage_returns_400(authed_client):
    client, user = authed_client
    r = client.put(
        "/api/v1/profile",
        {"birth_date": "2020-01-01"},
        format="json",
    )
    assert r.status_code == 400
    assert r.data["error"]["code"] == "VALIDATION_ERROR"


def test_put_profile_negative_income_returns_400(authed_client):
    client, user = authed_client
    r = client.put(
        "/api/v1/profile",
        {"monthly_income": "-100.00"},
        format="json",
    )
    assert r.status_code == 400


def test_put_profile_invalid_phone_returns_400(authed_client):
    client, user = authed_client
    r = client.put(
        "/api/v1/profile",
        {"phone": "not-a-phone"},
        format="json",
    )
    assert r.status_code == 400


def test_avatar_upload_success(authed_client):
    client, user = authed_client
    file = make_image_file(fmt="PNG", content_type="image/png")
    r = client.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
    assert r.status_code == 200
    assert r.data["avatar"].endswith(".jpg")

    user.profile.refresh_from_db()
    with Image.open(user.profile.avatar.path) as saved:
        assert saved.width <= 400 and saved.height <= 400


def test_avatar_upload_invalid_type_returns_400(authed_client):
    client, user = authed_client
    from django.core.files.uploadedfile import SimpleUploadedFile

    file = SimpleUploadedFile("avatar.txt", b"not an image", content_type="text/plain")
    r = client.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
    assert r.status_code == 400


def test_avatar_upload_too_large_returns_400(authed_client):
    client, user = authed_client
    file = make_image_file(
        fmt="JPEG", content_type="image/jpeg", size_bytes=3 * 1024 * 1024
    )
    r = client.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
    assert r.status_code == 400
