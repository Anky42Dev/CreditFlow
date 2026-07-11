"""
Интеграционные тесты флоу заявки: submit -> scoring -> APPROVED/MANUAL_REVIEW/REJECTED
-> (если одобрено) Loan + PaymentScheduleItem.

Построено на реальных apps/applications/services.py (submit_application, perform_scoring,
calc_annuity, compute_score), apps/applications/urls.py (basename "credit-application",
эндпоинт /api/v1/credit-applications), apps/lending/services.py (disburse_loan).

compute_score детерминирован (см. apps/applications/services.py::compute_score), поэтому
исход скоринга контролируется через profile.monthly_income относительно monthly_payment,
а не через мок скорингового движка:
  ratio = monthly_payment / monthly_income
  ratio < 0.2        -> score 800 -> APPROVED
  0.2 <= ratio < 0.4  -> score 600 -> MANUAL_REVIEW
  ratio >= 0.4        -> score 300 -> REJECTED

ASSUMPTION (views.py не был доступен): имя action'а submit на CreditApplicationViewSet —
"submit", итоговый путь /api/v1/credit-applications/{id}/submit. Сверить, если тест падает
с 404 на этом шаге.
"""
from decimal import Decimal

import pytest
from rest_framework import status

from apps.applications.models import CreditApplication, ScoringResult
from apps.applications.services import calc_annuity
from apps.lending.models import Loan, PaymentScheduleItem

pytestmark = pytest.mark.django_db

APPLICATIONS_URL = "/api/v1/credit-applications"  # без слэша — router(trailing_slash=False)


def _set_income_for_ratio(user, product, amount, term_months, ratio):
    """Подбирает profile.monthly_income так, чтобы monthly_payment/monthly_income == ratio."""
    monthly_payment = calc_annuity(amount, product.interest_rate, term_months)
    user.profile.monthly_income = (monthly_payment / Decimal(str(ratio))).quantize(Decimal("0.01"))
    user.profile.save()
    return monthly_payment


def _create_application(client_authed, product, amount, term_months):
    resp = client_authed.post(
        APPLICATIONS_URL,
        {"product": product.id, "amount": str(amount), "term_months": term_months},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    return resp.json()


def _submit(client_authed, application_id):
    resp = client_authed.post(f"{APPLICATIONS_URL}/{application_id}/submit")
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_202_ACCEPTED), resp.content
    return resp


class TestFullApprovalFlow:
    def test_auto_approved_flow_creates_loan_and_full_schedule(self, client_authed, user, product, celery_eager):
        amount, term_months = Decimal("200000.00"), 12
        _set_income_for_ratio(user, product, amount, term_months, ratio="0.15")  # -> APPROVED

        created = _create_application(client_authed, product, amount, term_months)
        application_id = created["id"]

        app_obj = CreditApplication.objects.get(id=application_id)
        assert app_obj.status == "DRAFT"

        _submit(client_authed, application_id)

        app_obj.refresh_from_db()
        scoring = ScoringResult.objects.get(application=app_obj)
        assert scoring.decision == "APPROVED"
        # perform_scoring вызывает disburse_loan прямо при APPROVED -> статус уходит в DISBURSED
        assert app_obj.status == "DISBURSED"

        loan = Loan.objects.get(application=app_obj)
        assert loan.status == "ACTIVE"
        assert loan.outstanding_balance == amount
        schedule_count = PaymentScheduleItem.objects.filter(loan=loan).count()
        assert schedule_count == term_months

    def test_manual_review_does_not_create_loan_until_approved(self, client_authed, user, product, celery_eager):
        amount, term_months = Decimal("200000.00"), 12
        _set_income_for_ratio(user, product, amount, term_months, ratio="0.3")  # -> MANUAL_REVIEW

        created = _create_application(client_authed, product, amount, term_months)
        application_id = created["id"]
        _submit(client_authed, application_id)

        app_obj = CreditApplication.objects.get(id=application_id)
        assert app_obj.status == "MANUAL_REVIEW"
        assert ScoringResult.objects.get(application=app_obj).decision == "MANUAL_REVIEW"
        assert not Loan.objects.filter(application=app_obj).exists()

    def test_rejected_flow_no_loan(self, client_authed, user, product, celery_eager):
        amount, term_months = Decimal("200000.00"), 12
        _set_income_for_ratio(user, product, amount, term_months, ratio="0.6")  # -> REJECTED

        created = _create_application(client_authed, product, amount, term_months)
        application_id = created["id"]
        _submit(client_authed, application_id)

        app_obj = CreditApplication.objects.get(id=application_id)
        assert app_obj.status == "REJECTED"
        assert ScoringResult.objects.get(application=app_obj).decision == "REJECTED"
        assert not Loan.objects.filter(application=app_obj).exists()

    def test_underwriter_approval_of_manual_review_creates_loan(
        self, client_authed, underwriter_client, user, product, celery_eager
    ):
        """MANUAL_REVIEW -> одобрение через admin API (approve_application) -> DISBURSED + Loan.

        ASSUMPTION: путь /api/v1/admin/applications/{id}/approve — сверить с
        apps/adminpanel/views.py::AdminApplicationViewSet, которого у меня пока нет.
        """
        amount, term_months = Decimal("200000.00"), 12
        _set_income_for_ratio(user, product, amount, term_months, ratio="0.3")  # -> MANUAL_REVIEW

        created = _create_application(client_authed, product, amount, term_months)
        application_id = created["id"]
        _submit(client_authed, application_id)

        app_obj = CreditApplication.objects.get(id=application_id)
        assert app_obj.status == "MANUAL_REVIEW"

        resp = underwriter_client.post(f"/api/v1/admin/applications/{application_id}/approve", {"comment": "OK"})
        assert resp.status_code == status.HTTP_200_OK, resp.content

        app_obj.refresh_from_db()
        assert app_obj.status == "DISBURSED"
        loan = Loan.objects.get(application=app_obj)
        assert PaymentScheduleItem.objects.filter(loan=loan).count() == term_months
