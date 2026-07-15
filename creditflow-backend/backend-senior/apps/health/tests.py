"""DOC 5 §13: /health/live, /health/ready, /health/startup."""

import pytest
from django.test import Client

from apps.health import checks, views

pytestmark = pytest.mark.django_db(databases=["default", "replica"])


class TestLiveness:
    def test_returns_ok(self):
        response = Client().get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestReadiness:
    def test_200_when_all_checks_pass(self, monkeypatch):
        monkeypatch.setattr(views, "check_db", lambda: True)
        monkeypatch.setattr(views, "check_replica_db", lambda: True)
        monkeypatch.setattr(views, "check_redis", lambda: True)
        monkeypatch.setattr(views, "check_broker", lambda: True)

        response = Client().get("/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "db": True,
            "replica_db": True,
            "redis": True,
            "broker": True,
        }

    def test_503_when_a_check_fails(self, monkeypatch):
        monkeypatch.setattr(views, "check_db", lambda: True)
        monkeypatch.setattr(views, "check_replica_db", lambda: True)
        monkeypatch.setattr(views, "check_redis", lambda: False)
        monkeypatch.setattr(views, "check_broker", lambda: True)

        response = Client().get("/health/ready")

        assert response.status_code == 503
        assert response.json()["redis"] is False

    def test_503_when_replica_db_unavailable(self, monkeypatch):
        """AC-10: БД-реплика недоступна → /health/ready → 503."""
        monkeypatch.setattr(views, "check_db", lambda: True)
        monkeypatch.setattr(views, "check_replica_db", lambda: False)
        monkeypatch.setattr(views, "check_redis", lambda: True)
        monkeypatch.setattr(views, "check_broker", lambda: True)

        response = Client().get("/health/ready")

        assert response.status_code == 503
        assert response.json()["replica_db"] is False


class TestStartup:
    def test_200_when_no_pending_migrations(self):
        response = Client().get("/health/startup")

        assert response.status_code == 200
        assert response.json() == {"migrations_applied": True}

    def test_503_when_migrations_are_pending(self, monkeypatch):
        monkeypatch.setattr(views, "check_migrations_applied", lambda: False)

        response = Client().get("/health/startup")

        assert response.status_code == 503


class TestChecks:
    def test_check_db_true_against_real_db(self):
        assert checks.check_db() is True

    def test_check_replica_db_true_against_real_db(self):
        assert checks.check_replica_db() is True

    def test_check_redis_uses_configured_cache(self):
        assert checks.check_redis() is True

    def test_check_broker_true_for_memory_transport(self, settings):
        settings.EVENT_BROKER_URL = "memory://"
        assert checks.check_broker() is True

    def test_check_broker_false_for_unreachable_broker(self, settings):
        settings.EVENT_BROKER_URL = "amqp://guest:guest@localhost:1/"
        assert checks.check_broker() is False
