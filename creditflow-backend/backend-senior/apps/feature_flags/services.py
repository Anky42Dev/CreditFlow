"""DOC 5 §11: Redis-backed feature flags with global + percentage rollout,
mirroring the doc's is_enabled() pseudocode. One Redis key per flag
(`feature_flag:{name}` -> JSON `{"global": bool, "percentage": int}`), on its
own DB index (settings.FEATURE_FLAGS_REDIS_URL) rather than CACHES["default"]
so an ops-side cache flush doesn't also reset flag state.
"""

import json
import zlib

import redis
from django.conf import settings

_KEY_PREFIX = "feature_flag:"


def _client() -> redis.Redis:
    return redis.Redis.from_url(settings.FEATURE_FLAGS_REDIS_URL, decode_responses=True)


def _key(flag: str) -> str:
    return f"{_KEY_PREFIX}{flag}"


def get_flag(flag: str) -> dict | None:
    raw = _client().get(_key(flag))
    if raw is None:
        return None
    return json.loads(raw)


def list_flags() -> dict:
    client = _client()
    keys = list(client.scan_iter(match=f"{_KEY_PREFIX}*"))
    if not keys:
        return {}
    values = client.mget(keys)
    return {
        key[len(_KEY_PREFIX) :]: json.loads(value)
        for key, value in zip(keys, values)
        if value is not None
    }


def set_flag(flag: str, *, global_: bool = False, percentage: int = 0) -> dict:
    cfg = {"global": global_, "percentage": percentage}
    _client().set(_key(flag), json.dumps(cfg))
    return cfg


def delete_flag(flag: str) -> None:
    _client().delete(_key(flag))


def is_enabled(flag: str, user=None) -> bool:
    """DOC 5 §11 pseudocode: a global flag is on for everyone; otherwise a
    user falls in the rollout when `user.id % 100 < percentage` — a stable
    per-user bucket rather than a random draw per call, so the same user
    always lands on the same side of the rollout."""
    cfg = get_flag(flag)
    if not cfg:
        return False
    if cfg.get("global"):
        return True
    if user is not None and getattr(user, "id", None) is not None:
        return user.id % 100 < cfg.get("percentage", 0)
    return False


def _pseudo_object_id(name: str) -> int:
    """AuditLog.object_id is a BigIntegerField (it's a loose, non-FK
    reference shared with real ORM rows) but flags are Redis-keyed by name,
    not a DB row with an integer pk — CRC32 gives a stable per-name int
    without standing up a Postgres table just for id assignment."""
    return zlib.crc32(name.encode())


def audit_flag_change(
    actor, name: str, before: dict | None, after: dict | None, request=None
) -> None:
    """DOC 5 §11 "аудит смены флага" / §10.5. Bypasses common.audit.audit_log
    since that helper expects a real model instance (`obj.pk`); flags have
    no ORM row to point at."""
    from apps.audit.models import AuditLog
    from common.audit import get_client_ip

    resolved_actor = actor if getattr(actor, "pk", None) else None
    AuditLog.objects.create(
        actor=resolved_actor,
        action="feature_flag.updated" if after is not None else "feature_flag.deleted",
        object_type="FeatureFlag",
        object_id=_pseudo_object_id(name),
        changes={"name": name, "before": before, "after": after},
        ip_address=get_client_ip(request),
    )
