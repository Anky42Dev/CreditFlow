from fastapi.testclient import TestClient

from scoring_service.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_endpoint_returns_decision():
    response = client.post(
        "/score",
        json={
            "application_id": 42,
            "monthly_payment": "10000",
            "monthly_income": "100000",
            "has_birth_date": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["application_id"] == 42
    assert body["decision"] == "APPROVED"
    assert body["score"] == 800


def test_score_endpoint_defaults_has_birth_date_false():
    response = client.post(
        "/score",
        json={"application_id": 7, "monthly_payment": "1000", "monthly_income": None},
    )
    assert response.status_code == 200
    body = response.json()
    # no income ratio (500) - no-birth-date penalty (100) = 400 -> below the
    # MANUAL_REVIEW threshold (500), so REJECTED.
    assert body["score"] == 400
    assert body["decision"] == "REJECTED"


def test_score_endpoint_rejects_non_positive_payment():
    response = client.post(
        "/score",
        json={"application_id": 8, "monthly_payment": "0", "monthly_income": "1000"},
    )
    assert response.status_code == 422
