"""DOC 5 §13: the three probes' underlying checks, kept separate from
views.py so tests can call them directly without going through the HTTP
layer.
"""

from django.conf import settings
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from kombu import Connection


def check_db() -> bool:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def check_replica_db() -> bool:
    """AC-10: pings the "replica" alias (config/settings.py::DATABASES) so
    readiness reflects the read replica specifically, not just the primary.
    """
    try:
        with connections["replica"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def check_redis() -> bool:
    from django.core.cache import cache

    try:
        cache.set("health_check_ping", "1", timeout=5)
        return cache.get("health_check_ping") == "1"
    except Exception:
        return False


def check_broker() -> bool:
    """Pings EVENT_BROKER_URL (DOC 5 §8.3) — RabbitMQ in docker-compose/prod,
    kombu's in-memory transport (always "connected") in dev/tests."""
    try:
        with Connection(
            getattr(settings, "EVENT_BROKER_URL", "memory://")
        ) as connection:
            connection.ensure_connection(max_retries=1, timeout=2)
        return True
    except Exception:
        return False


def check_migrations_applied() -> bool:
    executor = MigrationExecutor(connections["default"])
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    return not plan
