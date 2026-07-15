from decimal import Decimal

import pytest

from lending.domain.entities.application import CreditApplicationAggregate
from lending.domain.entities.product import CreditProduct
from lending.domain.events.application_approved import ApplicationApproved
from lending.domain.events.application_rejected import ApplicationRejected
from lending.domain.events.application_submitted import ApplicationSubmitted
from lending.domain.value_objects.application_status import ApplicationStatus
from lending.domain.value_objects.money import Money
from lending.domain.value_objects.term import Term
from shared.domain.errors import DomainError


def make_product(**overrides):
    defaults = dict(
        id=1,
        min_amount=Money(Decimal("10000")),
        max_amount=Money(Decimal("500000")),
        interest_rate=Decimal("12"),
        min_term_months=3,
        max_term_months=36,
    )
    defaults.update(overrides)
    return CreditProduct(**defaults)


def make_application(status=ApplicationStatus.DRAFT, **overrides):
    defaults = dict(
        id=1,
        user_id=42,
        product=make_product(),
        amount=Money(Decimal("100000")),
        term=Term(12),
        status=status,
    )
    defaults.update(overrides)
    return CreditApplicationAggregate(**defaults)


def test_submit_from_draft_computes_payment_and_raises_event():
    app = make_application()
    app.submit()
    assert app.status == ApplicationStatus.SUBMITTED
    assert app.monthly_payment is not None
    events = app.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], ApplicationSubmitted)
    assert events[0].application_id == 1
    assert events[0].user_id == 42


def test_submit_non_draft_rejected():
    app = make_application(status=ApplicationStatus.SUBMITTED)
    with pytest.raises(DomainError):
        app.submit()


def test_submit_amount_out_of_bounds_rejected():
    app = make_application(amount=Money(Decimal("1000000")))
    with pytest.raises(DomainError):
        app.submit()


def test_pull_events_clears_buffer():
    app = make_application()
    app.submit()
    app.pull_events()
    assert app.pull_events() == []


def test_start_scoring_from_submitted():
    app = make_application(status=ApplicationStatus.SUBMITTED)
    app.start_scoring()
    assert app.status == ApplicationStatus.SCORING


def test_start_scoring_from_draft_rejected():
    app = make_application(status=ApplicationStatus.DRAFT)
    with pytest.raises(DomainError):
        app.start_scoring()


def test_apply_scoring_decision_approved_raises_event():
    app = make_application(status=ApplicationStatus.SCORING)
    app.apply_scoring_decision(ApplicationStatus.APPROVED)
    assert app.status == ApplicationStatus.APPROVED
    events = app.pull_events()
    assert isinstance(events[0], ApplicationApproved)


def test_apply_scoring_decision_rejected_raises_event():
    app = make_application(status=ApplicationStatus.SCORING)
    app.apply_scoring_decision(ApplicationStatus.REJECTED)
    assert app.status == ApplicationStatus.REJECTED
    events = app.pull_events()
    assert isinstance(events[0], ApplicationRejected)


def test_apply_scoring_decision_manual_review_raises_no_event():
    app = make_application(status=ApplicationStatus.SCORING)
    app.apply_scoring_decision(ApplicationStatus.MANUAL_REVIEW)
    assert app.status == ApplicationStatus.MANUAL_REVIEW
    assert app.pull_events() == []


def test_apply_scoring_decision_invalid_value_rejected():
    app = make_application(status=ApplicationStatus.SCORING)
    with pytest.raises(DomainError):
        app.apply_scoring_decision(ApplicationStatus.DRAFT)


def test_approve_from_manual_review():
    app = make_application(status=ApplicationStatus.MANUAL_REVIEW)
    app.approve_from_manual_review()
    assert app.status == ApplicationStatus.APPROVED
    assert isinstance(app.pull_events()[0], ApplicationApproved)


def test_approve_from_manual_review_wrong_state_rejected():
    app = make_application(status=ApplicationStatus.DRAFT)
    with pytest.raises(DomainError):
        app.approve_from_manual_review()


def test_reject_from_manual_review():
    app = make_application(status=ApplicationStatus.MANUAL_REVIEW)
    app.reject_from_manual_review()
    assert app.status == ApplicationStatus.REJECTED
    assert isinstance(app.pull_events()[0], ApplicationRejected)


def test_reject_from_manual_review_wrong_state_rejected():
    app = make_application(status=ApplicationStatus.DRAFT)
    with pytest.raises(DomainError):
        app.reject_from_manual_review()


def test_mark_disbursed_from_approved():
    app = make_application(status=ApplicationStatus.APPROVED)
    app.mark_disbursed()
    assert app.status == ApplicationStatus.DISBURSED


def test_mark_disbursed_wrong_state_rejected():
    app = make_application(status=ApplicationStatus.SUBMITTED)
    with pytest.raises(DomainError):
        app.mark_disbursed()
