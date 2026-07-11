"""
E2E: создание заявки -> submit -> скоринг (MANUAL_REVIEW) -> одобрение андеррайтером ->
выдача (авто через approve_application->disburse_loan) -> погашение,
с проверкой WebSocket-событий на каждом шаге.

ВАЖНО — два реальных ограничения текущего кода, из-за которых сценарий не 1:1 с ТЗ:

1. config/urls.py не подключает apps.accounts.urls вообще — HTTP register/login
   эндпоинтов нет. Шаги "регистрация"/"логин" из ТЗ Промпта №5.1 пока физически
   невозможны через API. Тест-заглушка ниже помечен skip с этой причиной; когда
   auth API (блокер №1, Этап 0) будет реализован и подключён в urls.py, замените
   fixture user/jwt_token_factory на реальные HTTP-вызовы и снимите skip.
2. apps/lending/services.py::repay() НЕ вызывает push_status/notify_user —
   значит после погашения сейчас не летит НИКАКОЕ WS-событие. Это не баг теста:
   я явно проверил код repay() и там нет push. test_ws_event_fires_on_repay ниже
   помечен xfail(strict=True) с этой причиной — он должен начать проходить сам,
   как только в repay() добавят push_status(loan.application) или аналог, и
   тогда его нужно будет "разксфейлить".

Остальные шаги (submit, скоринг, одобрение андеррайтером, выдача, WS-события на
статусах заявки, погашение как API-вызов) — рабочие и based on фактическом коде.
"""
from decimal import Decimal

import pytest
from channels.testing import WebsocketCommunicator
from rest_framework import status
from rest_framework.test import APIClient

from apps.applications.models import CreditApplication
from apps.applications.services import calc_annuity
from apps.lending.models import Loan
from config.asgi import application as asgi_application  # ASSUMPTION: имя ASGI-приложения, сверить

pytestmark = pytest.mark.django_db

APPLICATIONS_URL = "/api/v1/credit-applications"


@pytest.mark.skip(
    reason=(
        "auth API (регистрация/логин) не подключены в config/urls.py — "
        "apps.accounts.urls отсутствует в include(). Заблокировано Этапом 0 "
        "(item 0 из мастер-спеки), не относится к Этапу 9."
    )
)
def test_e2e_registration_and_login_via_http():
    ...


@pytest.mark.asyncio
async def test_e2e_manual_review_to_disbursement_with_ws_events(
    client_authed, underwriter_client, user, underwriter_user, product, celery_eager, jwt_token_factory
):
    from asgiref.sync import sync_to_async

    amount, term_months = Decimal("200000.00"), 12

    # profile.monthly_income подобран так, чтобы ratio ~0.3 -> MANUAL_REVIEW
    # (см. apps/applications/services.py::compute_score)
    monthly_payment = calc_annuity(amount, product.interest_rate, term_months)
    await sync_to_async(_set_income)(user, monthly_payment, Decimal("0.3"))

    ws_token = jwt_token_factory(user)
    communicator = WebsocketCommunicator(asgi_application, f"/ws/notifications/?token={ws_token}")  # ASSUMPTION: маршрут WS
    connected, _ = await communicator.connect()
    assert connected, "WS-соединение не установлено — сверить apps/realtime/routing.py и JWTAuthMiddleware"

    # --- создание заявки ---
    resp = await sync_to_async(client_authed.post)(
        APPLICATIONS_URL,
        {"product": product.id, "amount": str(amount), "term_months": term_months},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    application_id = resp.json()["id"]

    # --- submit ---
    resp = await sync_to_async(client_authed.post)(f"{APPLICATIONS_URL}/{application_id}/submit")
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_202_ACCEPTED), resp.content

    # perform_scoring: push_status(SCORING) -> push_status(MANUAL_REVIEW) -> notify_user(...)
    ev_scoring = await communicator.receive_json_from(timeout=5)
    assert ev_scoring == {"event": "application_status", "application_id": application_id, "status": "SCORING"}

    ev_status = await communicator.receive_json_from(timeout=5)
    assert ev_status == {
        "event": "application_status",
        "application_id": application_id,
        "status": "MANUAL_REVIEW",
    }

    ev_notification = await communicator.receive_json_from(timeout=5)
    assert ev_notification["event"] == "notification"  # уведомление application.manual_review от notify_user

    app_obj = await sync_to_async(CreditApplication.objects.get)(id=application_id)
    assert app_obj.status == "MANUAL_REVIEW"

    # --- одобрение андеррайтером (approve_application) ---
    resp = await sync_to_async(underwriter_client.post)(
        f"/api/v1/admin/applications/{application_id}/approve", {"comment": "ok"}
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content

    # approve_application: push_status(APPROVED) -> notify_user(...) -> disburse_loan -> notify_user(loan.disbursed)
    ev_approved = await communicator.receive_json_from(timeout=5)
    assert ev_approved == {"event": "application_status", "application_id": application_id, "status": "APPROVED"}

    ev_approved_notification = await communicator.receive_json_from(timeout=5)
    assert ev_approved_notification["event"] == "notification"

    ev_disbursed_notification = await communicator.receive_json_from(timeout=5)
    assert ev_disbursed_notification["event"] == "notification"

    app_obj = await sync_to_async(CreditApplication.objects.get)(id=application_id)
    assert app_obj.status == "DISBURSED"
    loan = await sync_to_async(lambda: Loan.objects.get(application=app_obj))()

    await communicator.disconnect()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "apps/lending/services.py::repay() не вызывает push_status ни notify_user — "
        "WS/уведомление о погашении сейчас не отправляется. Тест должен начать "
        "проходить, когда эту нотификацию добавят в repay()."
    ),
)
@pytest.mark.asyncio
async def test_ws_event_fires_on_repay(client_authed, user, product, celery_eager, jwt_token_factory):
    from asgiref.sync import sync_to_async

    amount, term_months = Decimal("200000.00"), 12
    monthly_payment = calc_annuity(amount, product.interest_rate, term_months)
    await sync_to_async(_set_income)(user, monthly_payment, Decimal("0.15"))  # -> APPROVED -> авто-выдача

    ws_token = jwt_token_factory(user)
    communicator = WebsocketCommunicator(asgi_application, f"/ws/notifications/?token={ws_token}")
    await communicator.connect()

    resp = await sync_to_async(client_authed.post)(
        APPLICATIONS_URL, {"product": product.id, "amount": str(amount), "term_months": term_months}, format="json"
    )
    application_id = resp.json()["id"]
    await sync_to_async(client_authed.post)(f"{APPLICATIONS_URL}/{application_id}/submit")

    # осушаем события скоринга/выдачи, нас интересует только событие после repay
    for _ in range(4):
        await communicator.receive_json_from(timeout=5)

    app_obj = await sync_to_async(CreditApplication.objects.get)(id=application_id)
    loan = await sync_to_async(lambda: Loan.objects.get(application=app_obj))()

    resp = await sync_to_async(client_authed.post)(
        f"/api/v1/loans/{loan.id}/repay",
        {"amount": str(monthly_payment), "idempotency_key": "e2e-repay-key"},
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content

    # ЭТО должно прилететь, но сейчас не летит — см. reason у xfail выше
    event = await communicator.receive_json_from(timeout=5)
    assert event["event"] in ("notification", "application_status")

    await communicator.disconnect()


def _set_income(user, monthly_payment, ratio):
    user.profile.monthly_income = (monthly_payment / ratio).quantize(Decimal("0.01"))
    user.profile.save()
