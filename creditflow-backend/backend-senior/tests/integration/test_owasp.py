"""DOC 5 §10.1, Roadmap Этап 6 п.16: regression tests for the OWASP Top 10
risks the doc calls out — Broken Access Control (IDOR), Injection, and mass
assignment (a Broken Access Control variant: writing fields a client should
never control). Uses the same fixtures as the rest of tests/integration
(conftest.py) rather than force_authenticate-ing ad hoc.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CreditApplication
from apps.lending.models import Loan
from apps.rbac.services import assign_role


def _other_client(email="other-client@example.com"):
    user = User.objects.create_user(email=email, password="TestPass123!")
    assign_role(user, "CLIENT")
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


@pytest.fixture
def application(user, product):
    return CreditApplication.objects.create(
        user=user, product=product, amount=Decimal("50000.00"), term_months=12
    )


@pytest.fixture
def loan(user, application):
    return Loan.objects.create(
        application=application,
        user=user,
        principal=Decimal("50000.00"),
        interest_rate=Decimal("18.50"),
        term_months=12,
        monthly_payment=Decimal("4600.00"),
        outstanding_balance=Decimal("50000.00"),
        status="ACTIVE",
        disbursed_at=timezone.now(),
    )


@pytest.mark.django_db
class TestIDOR:
    """A user must never be able to read/modify/delete another user's
    objects by guessing/incrementing an ID — CreditApplicationViewSet and
    LoanViewSet scope get_queryset() to request.user, so cross-tenant access
    should look like the object doesn't exist (404), not 403 (which would
    itself leak that the ID is valid)."""

    def test_cannot_read_another_users_application(self, application):
        _, other = _other_client()
        r = other.get(f"/api/v1/credit-applications/{application.id}")
        assert r.status_code == 404

    def test_cannot_list_another_users_application(self, application):
        _, other = _other_client()
        r = other.get("/api/v1/credit-applications")
        ids = [row["id"] for row in r.data["results"]]
        assert application.id not in ids

    def test_cannot_update_another_users_application(self, application):
        _, other = _other_client()
        r = other.put(
            f"/api/v1/credit-applications/{application.id}",
            {"amount": "1.00", "term_months": 3, "purpose": "hijacked"},
        )
        assert r.status_code == 404
        application.refresh_from_db()
        assert application.purpose != "hijacked"

    def test_cannot_delete_another_users_application(self, application):
        _, other = _other_client()
        r = other.delete(f"/api/v1/credit-applications/{application.id}")
        assert r.status_code == 404
        assert CreditApplication.objects.filter(id=application.id).exists()

    def test_cannot_submit_another_users_application(self, application):
        _, other = _other_client()
        r = other.post(f"/api/v1/credit-applications/{application.id}/submit")
        assert r.status_code == 404

    def test_cannot_read_another_users_loan(self, loan):
        _, other = _other_client()
        r = other.get(f"/api/v1/loans/{loan.id}")
        assert r.status_code == 404

    def test_cannot_list_another_users_loan(self, loan):
        _, other = _other_client()
        r = other.get("/api/v1/loans")
        ids = [row["id"] for row in r.data["results"]]
        assert loan.id not in ids


@pytest.mark.django_db
class TestMassAssignment:
    """The create/update serializers whitelist writable fields explicitly
    (apps/applications/serializers.py) — a client trying to smuggle
    `status`/`user` in the body must not be able to set them."""

    def test_create_ignores_injected_status_and_user(self, client_authed, product):
        other_user, _ = _other_client("victim@example.com")
        r = client_authed.post(
            "/api/v1/credit-applications",
            {
                "product": product.id,
                "amount": "50000.00",
                "term_months": 12,
                "purpose": "test",
                "status": "APPROVED",
                "user": other_user.id,
            },
        )
        assert r.status_code == 201
        created = CreditApplication.objects.get(id=r.data["id"])
        assert created.status == "DRAFT"
        assert created.user_id != other_user.id

    def test_update_ignores_injected_status(self, client_authed, application):
        r = client_authed.put(
            f"/api/v1/credit-applications/{application.id}",
            {"amount": "60000.00", "term_months": 12, "purpose": "ok", "status": "APPROVED"},
        )
        assert r.status_code == 200
        application.refresh_from_db()
        assert application.status == "DRAFT"


@pytest.mark.django_db
class TestInjection:
    """ORM query construction is parameterized end-to-end — a SQLi payload
    in a filter/search param must be treated as an inert string, never break
    the query or return data outside the requester's own scope."""

    SQLI_PAYLOADS = [
        "'; DROP TABLE credit_applications; --",
        "' OR '1'='1",
        "1 UNION SELECT * FROM users --",
    ]

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_search_param_is_inert(self, client_authed, application, payload):
        r = client_authed.get("/api/v1/credit-applications", {"search": payload})
        assert r.status_code == 200
        # table survives an attempted DROP TABLE payload
        assert CreditApplication.objects.filter(id=application.id).exists()

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_status_filter_is_inert(self, client_authed, application, payload):
        r = client_authed.get("/api/v1/credit-applications", {"status": payload})
        assert r.status_code in (200, 400)
