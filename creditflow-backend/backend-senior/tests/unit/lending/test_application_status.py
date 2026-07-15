import pytest

from lending.domain.value_objects.application_status import ApplicationStatus


@pytest.mark.parametrize(
    "source,target",
    [
        (ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED),
        (ApplicationStatus.SUBMITTED, ApplicationStatus.SCORING),
        (ApplicationStatus.SCORING, ApplicationStatus.APPROVED),
        (ApplicationStatus.SCORING, ApplicationStatus.MANUAL_REVIEW),
        (ApplicationStatus.SCORING, ApplicationStatus.REJECTED),
        (ApplicationStatus.MANUAL_REVIEW, ApplicationStatus.APPROVED),
        (ApplicationStatus.MANUAL_REVIEW, ApplicationStatus.REJECTED),
        (ApplicationStatus.APPROVED, ApplicationStatus.DISBURSED),
    ],
)
def test_allowed_transitions(source, target):
    assert source.can_transition_to(target)


@pytest.mark.parametrize(
    "source,target",
    [
        (ApplicationStatus.DRAFT, ApplicationStatus.APPROVED),
        (ApplicationStatus.DRAFT, ApplicationStatus.DISBURSED),
        (ApplicationStatus.SUBMITTED, ApplicationStatus.APPROVED),
        (ApplicationStatus.REJECTED, ApplicationStatus.APPROVED),
        (ApplicationStatus.DISBURSED, ApplicationStatus.APPROVED),
    ],
)
def test_disallowed_transitions(source, target):
    assert not source.can_transition_to(target)
