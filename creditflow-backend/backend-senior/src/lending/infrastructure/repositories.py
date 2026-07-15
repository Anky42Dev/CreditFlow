from apps.applications.models import CreditApplication as CreditApplicationModel
from apps.lending.models import Loan as LoanModel

from ..domain.entities.application import CreditApplicationAggregate
from ..domain.repositories.application_repository import ApplicationRepository
from ..domain.repositories.loan_repository import LoanRepository
from .mappers import ApplicationMapper

# Superset of every select_related the Submit/Approve/Reject legacy services
# touch (product for annuity/bounds, user/user__profile for notify_user,
# scoring_result for the admin detail serializer) so get_model() doesn't
# reintroduce N+1 queries regardless of which of the three calls it.
_APPLICATION_SELECT_RELATED = ("product", "user", "user__profile", "scoring_result")


class DjangoApplicationRepository(ApplicationRepository):
    def get(self, application_id: int) -> CreditApplicationAggregate:
        model = CreditApplicationModel.objects.select_related("product").get(
            id=application_id
        )
        return ApplicationMapper.to_domain(model)

    def get_model(self, application_id: int) -> CreditApplicationModel:
        return CreditApplicationModel.objects.select_related(
            *_APPLICATION_SELECT_RELATED
        ).get(id=application_id)

    def save(self, aggregate: CreditApplicationAggregate) -> None:
        model = CreditApplicationModel.objects.get(id=aggregate.id)
        ApplicationMapper.to_model(aggregate, model)
        model.save(update_fields=["status", "monthly_payment"])


class DjangoLoanRepository(LoanRepository):
    def get(self, loan_id: int) -> LoanModel:
        return LoanModel.objects.get(id=loan_id)

    def save(self, loan: LoanModel) -> None:
        loan.save()
