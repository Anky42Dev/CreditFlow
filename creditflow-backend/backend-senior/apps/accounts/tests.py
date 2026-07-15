import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .models import User
from .services import register_user


def make_image_file(fmt="PNG", content_type="image/png", size_bytes=None):
    image = Image.new("RGB", (500, 500), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    content = buffer.getvalue()
    if size_bytes:
        content += b"0" * max(0, size_bytes - len(content))
    return SimpleUploadedFile("avatar." + fmt.lower(), content, content_type=content_type)


class RegisterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_client_user(self):
        r = self.client.post(
            "/api/v1/auth/register",
            {"email": "a@b.com", "password": "StrongPass123"},
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["email"], "a@b.com")
        self.assertEqual(r.data["role"], "CLIENT")
        self.assertTrue(User.objects.get(email="a@b.com").check_password("StrongPass123"))

    def test_register_also_creates_empty_profile(self):
        self.client.post(
            "/api/v1/auth/register",
            {"email": "a@b.com", "password": "StrongPass123"},
        )
        user = User.objects.get(email="a@b.com")
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.first_name, "")

    def test_register_duplicate_email_returns_409(self):
        User.objects.create_user(email="a@b.com", password="StrongPass123")
        r = self.client.post(
            "/api/v1/auth/register",
            {"email": "a@b.com", "password": "StrongPass123"},
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["error"]["code"], "EMAIL_TAKEN")

    def test_register_weak_password_returns_400(self):
        r = self.client.post(
            "/api/v1/auth/register",
            {"email": "a@b.com", "password": "12345678"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["error"]["code"], "VALIDATION_ERROR")


class LoginRefreshTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_success_returns_access_and_refresh(self):
        User.objects.create_user(email="a@b.com", password="StrongPass123")
        r = self.client.post(
            "/api/v1/auth/login",
            {"email": "a@b.com", "password": "StrongPass123"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)

    def test_login_invalid_credentials_returns_401(self):
        User.objects.create_user(email="a@b.com", password="StrongPass123")
        r = self.client.post(
            "/api/v1/auth/login",
            {"email": "a@b.com", "password": "WrongPass123"},
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data["error"]["code"], "AUTHENTICATION_FAILED")

    def test_refresh_returns_new_access_token(self):
        User.objects.create_user(email="a@b.com", password="StrongPass123")
        login = self.client.post(
            "/api/v1/auth/login",
            {"email": "a@b.com", "password": "StrongPass123"},
        )
        r = self.client.post("/api/v1/auth/refresh", {"refresh": login.data["refresh"]})
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_refresh_invalid_token_returns_401_token_expired(self):
        r = self.client.post("/api/v1/auth/refresh", {"refresh": "not-a-real-token"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data["error"]["code"], "TOKEN_EXPIRED")


class CookieAuthTests(TestCase):
    """DOC 6 §3: refresh lives in an httpOnly cookie; access stays in the body
    for the frontend to hold in memory. Legacy body-refresh (Junior/Middle)
    must keep working untouched.
    """

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        User.objects.create_user(email="a@b.com", password="StrongPass123")

    def login(self):
        return self.client.post(
            "/api/v1/auth/login",
            {"email": "a@b.com", "password": "StrongPass123"},
        )

    def test_login_sets_httponly_refresh_cookie(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        cookie = r.cookies["cf_refresh_token"]
        self.assertEqual(cookie.value, r.data["refresh"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")

    def test_login_sets_csrf_cookie(self):
        r = self.login()
        self.assertIn("csrftoken", r.cookies)

    def test_refresh_via_cookie_with_csrf_token_succeeds(self):
        self.login()
        csrf_token = self.client.cookies["csrftoken"].value
        r = self.client.post(
            "/api/v1/auth/refresh",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertNotIn("refresh", r.data)

    def test_refresh_via_cookie_without_csrf_token_returns_403(self):
        self.login()
        r = self.client.post("/api/v1/auth/refresh", {}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_refresh_without_cookie_or_body_returns_401(self):
        r = self.client.post("/api/v1/auth/refresh", {}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_legacy_body_refresh_still_works_without_csrf_token(self):
        login = self.login()
        r = self.client.post(
            "/api/v1/auth/refresh",
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_logout_clears_refresh_cookie(self):
        self.login()
        csrf_token = self.client.cookies["csrftoken"].value
        r = self.client.post(
            "/api/v1/auth/logout",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.cookies["cf_refresh_token"].value, "")

    def test_logout_without_csrf_token_returns_403(self):
        self.login()
        r = self.client.post("/api/v1/auth/logout", {}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_logout_without_prior_login_is_a_noop(self):
        anon = APIClient(enforce_csrf_checks=True)
        r = anon.post("/api/v1/auth/logout", {}, format="json")
        self.assertEqual(r.status_code, 204)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = register_user(email="a@b.com", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_profile_requires_auth(self):
        anon = APIClient()
        r = anon.get("/api/v1/profile")
        self.assertEqual(r.status_code, 401)

    def test_get_profile_returns_user_and_profile_data(self):
        r = self.client.get("/api/v1/profile")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["email"], "a@b.com")
        self.assertEqual(r.data["role"], "CLIENT")
        self.assertEqual(r.data["first_name"], "")

    def test_put_profile_updates_fields(self):
        r = self.client.put(
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
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["first_name"], "Иван")
        self.assertEqual(r.data["monthly_income"], "80000.00")

    def test_put_profile_cannot_change_role(self):
        r = self.client.put(
            "/api/v1/profile",
            {"role": "ADMIN"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "CLIENT")

    def test_put_profile_underage_returns_400(self):
        r = self.client.put(
            "/api/v1/profile",
            {"birth_date": "2020-01-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["error"]["code"], "VALIDATION_ERROR")

    def test_put_profile_negative_income_returns_400(self):
        r = self.client.put(
            "/api/v1/profile",
            {"monthly_income": "-100.00"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_put_profile_invalid_phone_returns_400(self):
        r = self.client.put(
            "/api/v1/profile",
            {"phone": "not-a-phone"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)


CELERY_EAGER = {"CELERY_TASK_ALWAYS_EAGER": True, "CELERY_TASK_EAGER_PROPAGATES": True}
# process_avatar (Этап 5 §9) calls push_avatar_updated, which needs a channel
# layer; swap in-memory so these tests don't require a real Redis instance.
TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), **CELERY_EAGER, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class AvatarUploadTests(TestCase):
    def setUp(self):
        self.user = register_user(email="a@b.com", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_avatar_upload_queues_processing_and_resizes_in_the_background(self):
        """DOC 5 §9: the request only confirms the task was queued (202); with
        CELERY_TASK_ALWAYS_EAGER the task itself already ran by the time
        .delay() returns, so the resize can be asserted directly here — in
        production it completes later and the client learns via WS push
        (see apps.realtime.tests.PushAvatarUpdatedDeliveryTests)."""
        file = make_image_file(fmt="PNG", content_type="image/png")
        r = self.client.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.data["status"], "processing")

        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar.name.endswith(".jpg"))
        with Image.open(self.user.profile.avatar.path) as saved:
            self.assertTrue(saved.width <= 400 and saved.height <= 400)

    def test_avatar_upload_invalid_type_returns_400(self):
        file = SimpleUploadedFile("avatar.txt", b"not an image", content_type="text/plain")
        r = self.client.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_avatar_upload_too_large_returns_400(self):
        file = make_image_file(fmt="JPEG", content_type="image/jpeg", size_bytes=3 * 1024 * 1024)
        r = self.client.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_avatar_upload_requires_auth(self):
        anon = APIClient()
        file = make_image_file()
        r = anon.post("/api/v1/profile/avatar", {"avatar": file}, format="multipart")
        self.assertEqual(r.status_code, 401)
