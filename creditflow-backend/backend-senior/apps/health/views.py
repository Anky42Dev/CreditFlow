"""DOC 5 §13: /health/live, /health/ready, /health/startup."""

from django.http import JsonResponse

from .checks import (
    check_broker,
    check_db,
    check_migrations_applied,
    check_redis,
    check_replica_db,
)


def liveness(request):
    return JsonResponse({"status": "ok"})


def readiness(request):
    checks = {
        "db": check_db(),
        "replica_db": check_replica_db(),
        "redis": check_redis(),
        "broker": check_broker(),
    }
    status = 200 if all(checks.values()) else 503
    return JsonResponse(checks, status=status)


def startup(request):
    migrations_applied = check_migrations_applied()
    status = 200 if migrations_applied else 503
    return JsonResponse({"migrations_applied": migrations_applied}, status=status)
