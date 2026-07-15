"""DOC 5 §11: Redis-backed feature flags (global + percentage rollout) and
the admin API + audit trail on top of them. Redis itself is faked
(fakeredis) so these tests don't need a real Redis instance running.
"""

from types import SimpleNamespace

import pytest
from fakeredis import FakeRedis

from apps.feature_flags import services


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis(decode_responses=True)
    monkeypatch.setattr(services, "_client", lambda: client)
    return client


class TestIsEnabled:
    def test_false_when_flag_missing(self, fake_redis):
        assert services.is_enabled("unknown_flag") is False

    def test_global_flag_enabled_for_everyone(self, fake_redis):
        services.set_flag("kafka_events", global_=True)

        assert services.is_enabled("kafka_events") is True
        assert services.is_enabled("kafka_events", user=SimpleNamespace(id=1)) is True

    def test_percentage_rollout_is_stable_per_user(self, fake_redis):
        services.set_flag("new_scoring_model", percentage=50)

        assert (
            services.is_enabled("new_scoring_model", user=SimpleNamespace(id=10))
            is True
        )
        assert (
            services.is_enabled("new_scoring_model", user=SimpleNamespace(id=90))
            is False
        )

    def test_percentage_rollout_without_user_is_false(self, fake_redis):
        services.set_flag("instant_disbursement", percentage=100)

        assert services.is_enabled("instant_disbursement") is False


class TestFlagCrud:
    def test_set_get_list_delete_flag(self, fake_redis):
        services.set_flag("flag_a", global_=True, percentage=0)

        assert services.get_flag("flag_a") == {"global": True, "percentage": 0}
        assert services.list_flags() == {"flag_a": {"global": True, "percentage": 0}}

        services.delete_flag("flag_a")

        assert services.get_flag("flag_a") is None
        assert services.list_flags() == {}


@pytest.mark.django_db
class TestFeatureFlagAdminAPI:
    def test_list_and_detail_require_permission(self, underwriter_client, fake_redis):
        assert underwriter_client.get("/api/v1/admin/feature-flags").status_code == 403
        assert (
            underwriter_client.get(
                "/api/v1/admin/feature-flags/kafka_events"
            ).status_code
            == 403
        )

    def test_admin_can_crud_a_flag(self, admin_client, fake_redis):
        create = admin_client.put(
            "/api/v1/admin/feature-flags/kafka_events",
            {"is_global": True, "percentage": 0},
            format="json",
        )
        assert create.status_code == 200
        assert create.data == {"name": "kafka_events", "global": True, "percentage": 0}

        get = admin_client.get("/api/v1/admin/feature-flags/kafka_events")
        assert get.status_code == 200

        listing = admin_client.get("/api/v1/admin/feature-flags")
        assert listing.status_code == 200
        assert listing.data == [
            {"name": "kafka_events", "global": True, "percentage": 0}
        ]

        delete = admin_client.delete("/api/v1/admin/feature-flags/kafka_events")
        assert delete.status_code == 204

        assert (
            admin_client.get("/api/v1/admin/feature-flags/kafka_events").status_code
            == 404
        )

    def test_updating_a_flag_writes_an_audit_log(self, admin_client, fake_redis):
        from apps.audit.models import AuditLog

        admin_client.put(
            "/api/v1/admin/feature-flags/instant_disbursement",
            {"is_global": False, "percentage": 25},
            format="json",
        )

        log = AuditLog.objects.get(
            object_type="FeatureFlag", action="feature_flag.updated"
        )
        assert log.changes["name"] == "instant_disbursement"
        assert log.changes["after"] == {"global": False, "percentage": 25}
        assert log.actor_id is not None

    def test_deleting_a_flag_writes_an_audit_log(self, admin_client, fake_redis):
        from apps.audit.models import AuditLog

        admin_client.put(
            "/api/v1/admin/feature-flags/kafka_events",
            {"is_global": True, "percentage": 0},
            format="json",
        )
        admin_client.delete("/api/v1/admin/feature-flags/kafka_events")

        log = AuditLog.objects.get(
            object_type="FeatureFlag", action="feature_flag.deleted"
        )
        assert log.changes["after"] is None
