"""
Общие фикстуры для интеграционных/E2E тестов backend-middle.

Построено на основе реальных apps/applications/models.py, apps/lending/models.py,
apps/lending/services.py, config/settings.py, config/urls.py и стиля apps/lending/tests.py
(которые прислал пользователь). Там, где нужного файла ещё не было
(apps/applications/services.py, apps/applications/urls.py, apps/adminpanel/*,
apps/rbac/services.py напрямую), помечено # ASSUMPTION — сверить перед использованием.
"""
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.products.models import CreditProduct
from apps.rbac.services import assign_role  # подтверждено использованием в apps/lending/tests.py

# Совпадает с TEST_CACHES / TEST_CHANNEL_LAYERS из apps/lending/tests.py —
# чтобы тесты не требовали настоящего Redis.
TEST_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@pytest.fixture(autouse=True)
def _test_infra(db, settings):
    """Автоматически на каждый тест: локальный кэш вместо Redis (RBAC-кэш
    в common/permissions.py), in-memory channel layer вместо Redis Channels,
    и сид ролей/прав (без него assign_role/HasPermission не сработают)."""
    settings.CACHES = TEST_CACHES
    settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
    cache.clear()
    call_command("seed_rbac")


@pytest.fixture
def celery_eager(settings):
    """Синхронное выполнение celery-задач (скоринг, email, cron) внутри теста."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    return settings


@pytest.fixture
def product(db):
    """Активный кредитный продукт. Поля 1:1 с make_product() из apps/lending/tests.py."""
    return CreditProduct.objects.create(
        name="Потребительский",
        slug="consumer",
        min_amount=Decimal("10000.00"),
        max_amount=Decimal("500000.00"),
        interest_rate=Decimal("18.50"),
        min_term_months=3,
        max_term_months=36,
        is_active=True,
    )


def _make_user(email, role, monthly_income=None, birth_date=None):
    """Аналог make_user_with_profile() из apps/lending/tests.py + назначение роли."""
    user = User.objects.create_user(email=email, password="TestPass123!")
    if hasattr(user, "profile"):
        profile = user.profile
        if monthly_income is not None:
            profile.monthly_income = monthly_income
        if birth_date is not None:
            profile.birth_date = birth_date
        profile.save()
    assign_role(user, role)
    return user


@pytest.fixture
def user(db):
    """Обычный клиент (заявитель) с доходом/датой рождения, достаточными для скоринга."""
    return _make_user(
        "client@example.com",
        role="CLIENT",
        monthly_income=Decimal("100000.00"),
        birth_date="1990-01-01",
    )


@pytest.fixture
def underwriter_user(db):
    return _make_user("underwriter@example.com", role="UNDERWRITER")


@pytest.fixture
def admin_user(db):
    return _make_user("admin@example.com", role="ADMIN")


@pytest.fixture
def client_authed(user):
    """DRF APIClient от лица обычного клиента. force_authenticate — как в
    apps/lending/tests.py::LoanAPITests, а не реальный JWT-логин (эндпоинтов
    /auth/register //auth/login сейчас нет в config/urls.py — см. auth_client_via_jwt
    ниже, если тесту нужен настоящий токен, например для WebSocket)."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def underwriter_client(underwriter_user):
    client = APIClient()
    client.force_authenticate(user=underwriter_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def jwt_token_factory():
    """Выдаёт настоящий access-токен (не force_authenticate) для сценариев,
    которым нужен реальный JWT — в первую очередь apps.realtime.JWTAuthMiddleware
    для WebSocket-подключений (токен передаётся в query ?token=)."""

    def _make(user):
        return str(RefreshToken.for_user(user).access_token)

    return _make
