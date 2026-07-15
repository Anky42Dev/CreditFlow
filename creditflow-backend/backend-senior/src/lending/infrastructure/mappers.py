from apps.applications.models import CreditApplication as CreditApplicationModel
from apps.products.models import CreditProduct as CreditProductModel

from ..domain.entities.application import CreditApplicationAggregate
from ..domain.entities.product import CreditProduct
from ..domain.value_objects.application_status import ApplicationStatus
from ..domain.value_objects.money import Money
from ..domain.value_objects.term import Term


class ProductMapper:
    """DOC 5 §5.2. ORM <-> domain for apps.products.models.CreditProduct."""

    @staticmethod
    def to_domain(model: CreditProductModel) -> CreditProduct:
        return CreditProduct(
            id=model.id,
            min_amount=Money(model.min_amount),
            max_amount=Money(model.max_amount),
            interest_rate=model.interest_rate,
            min_term_months=model.min_term_months,
            max_term_months=model.max_term_months,
            is_active=model.is_active,
        )


class ApplicationMapper:
    """DOC 5 §5.2. ORM <-> domain for apps.applications.models.CreditApplication.
    `to_model` only applies the aggregate's own mutable fields (status,
    monthly_payment) onto an already-fetched instance — it leaves user/product
    FKs, purpose, created_at and submitted_at untouched, since the aggregate
    doesn't track them and a full field overwrite would risk clobbering data
    the aggregate never saw.
    """

    @staticmethod
    def to_domain(model: CreditApplicationModel) -> CreditApplicationAggregate:
        return CreditApplicationAggregate(
            id=model.id,
            user_id=model.user_id,
            product=ProductMapper.to_domain(model.product),
            amount=Money(model.amount),
            term=Term(model.term_months),
            status=ApplicationStatus(model.status),
            monthly_payment=(
                Money(model.monthly_payment)
                if model.monthly_payment is not None
                else None
            ),
        )

    @staticmethod
    def to_model(
        aggregate: CreditApplicationAggregate, model: CreditApplicationModel
    ) -> CreditApplicationModel:
        model.status = aggregate.status.value
        model.monthly_payment = (
            aggregate.monthly_payment.amount
            if aggregate.monthly_payment is not None
            else None
        )
        return model
