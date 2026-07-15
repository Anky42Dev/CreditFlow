"""DOC 5 §6.2, Roadmap Этап 2 п.5: the lending DI container resolves each use
case with its repository/UnitOfWork dependencies wired in."""

from lending.application.approve_application import ApproveApplicationUseCase
from lending.application.reject_application import RejectApplicationUseCase
from lending.application.repay_loan import RepayLoanUseCase
from lending.application.submit_application import SubmitApplicationUseCase
from lending.infrastructure.di import container
from lending.infrastructure.repositories import (
    DjangoApplicationRepository,
    DjangoLoanRepository,
)
from shared.infrastructure.unit_of_work import DjangoUnitOfWork


def test_submit_application_resolves_with_dependencies():
    use_case = container.submit_application()
    assert isinstance(use_case, SubmitApplicationUseCase)
    assert isinstance(use_case.repo, DjangoApplicationRepository)
    assert isinstance(use_case.uow, DjangoUnitOfWork)


def test_approve_application_resolves_with_dependencies():
    use_case = container.approve_application()
    assert isinstance(use_case, ApproveApplicationUseCase)
    assert isinstance(use_case.repo, DjangoApplicationRepository)


def test_reject_application_resolves_with_dependencies():
    use_case = container.reject_application()
    assert isinstance(use_case, RejectApplicationUseCase)
    assert isinstance(use_case.repo, DjangoApplicationRepository)


def test_repay_loan_resolves_with_dependencies():
    use_case = container.repay_loan()
    assert isinstance(use_case, RepayLoanUseCase)
    assert isinstance(use_case.repo, DjangoLoanRepository)


def test_factories_return_fresh_use_case_instances():
    assert container.submit_application() is not container.submit_application()
