from scoring_service.consumers.application_submitted import handle_application_submitted


def test_handle_application_submitted_computes_decision():
    payload = {
        "application_id": 42,
        "user_id": 7,
        "amount": "200000.00",
        "term_months": 12,
        "monthly_payment": "10000.00",
        "monthly_income": "100000.00",
        "has_birth_date": True,
    }

    result = handle_application_submitted(payload)

    assert result == {
        "application_id": 42,
        "score": 800,
        "decision": "APPROVED",
        "reason": "Sufficient income",
        "trace_id": None,
    }


def test_handle_application_submitted_passes_trace_id_through():
    """DOC 5 §12.3: ScoringCompleted carries whatever trace_id
    ApplicationSubmitted arrived with, unchanged."""
    payload = {
        "application_id": 42,
        "monthly_payment": "10000.00",
        "monthly_income": "100000.00",
        "has_birth_date": True,
        "trace_id": "11111111-1111-1111-1111-111111111111",
    }

    result = handle_application_submitted(payload)

    assert result["trace_id"] == "11111111-1111-1111-1111-111111111111"


def test_handle_application_submitted_handles_missing_income():
    payload = {
        "application_id": 43,
        "user_id": 8,
        "monthly_payment": "5000.00",
        "monthly_income": None,
        "has_birth_date": False,
    }

    result = handle_application_submitted(payload)

    assert result["score"] == 400
    assert result["decision"] == "REJECTED"


class _FakeEventBus:
    def __init__(self, incoming: list[dict]):
        self._incoming = list(incoming)
        self.published = []

    def consume_one(self, event_type, timeout=1.0):
        assert event_type == "ApplicationSubmitted"
        if not self._incoming:
            return None
        return self._incoming.pop(0)

    def publish(self, event_type, payload):
        self.published.append((event_type, payload))


def test_consume_once_publishes_scoring_completed(monkeypatch):
    from scoring_service.consumers import application_submitted as module

    fake_bus = _FakeEventBus(
        [
            {
                "application_id": 1,
                "monthly_payment": "10000.00",
                "monthly_income": "100000.00",
                "has_birth_date": True,
            }
        ]
    )
    monkeypatch.setattr(module, "get_event_bus", lambda: fake_bus)

    processed = module.consume_once(timeout=0.1)

    assert processed is True
    assert len(fake_bus.published) == 1
    event_type, payload = fake_bus.published[0]
    assert event_type == "ScoringCompleted"
    assert payload["application_id"] == 1
    assert payload["decision"] == "APPROVED"


def test_consume_once_returns_false_when_queue_empty(monkeypatch):
    from scoring_service.consumers import application_submitted as module

    fake_bus = _FakeEventBus([])
    monkeypatch.setattr(module, "get_event_bus", lambda: fake_bus)

    assert module.consume_once(timeout=0.1) is False
    assert fake_bus.published == []
