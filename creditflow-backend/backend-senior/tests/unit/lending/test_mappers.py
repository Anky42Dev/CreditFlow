"""DOC 5 §5.2 mapper round-trips. Uses unsaved Django model instances (FKs
assigned in-memory) so these run without a DB connection, like the rest of
tests/unit/ — the same pattern Этап 1's aggregate tests already rely on.
"""

from decimal import Decimal

from apps.applications.models import CreditApplication as CreditApplicationModel
from apps.products.models import CreditProduct as CreditProductModel

from lending.domain.value_objects.application_status import ApplicationStatus
from lending.domain.value_objects.money import Money
from lending.infrastructure.mappers import ApplicationMapper, ProductMapper


def make_product_model(**overrides):
    defaults = dict(
        id=1,
        name="Потребительский",
        slug="consumer",
        min_amount=Decimal("10000.00"),
        max_amount=Decimal("500000.00"),
        interest_rate=Decimal("18.50"),
        min_term_months=3,
        max_term_months=36,
        is_active=True,
    )
    defaults.update(overrides)
    return CreditProductModel(**defaults)


def make_application_model(**overrides):
    defaults = dict(
        id=7,
        user_id=42,
        product=make_product_model(),
        amount=Decimal("100000.00"),
        term_months=12,
        status="DRAFT",
        monthly_payment=None,
    )
    defaults.update(overrides)
    return CreditApplicationModel(**defaults)


def test_product_mapper_to_domain():
    model = make_product_model()
    product = ProductMapper.to_domain(model)
    assert product.id == 1
    assert product.min_amount == Money(Decimal("10000.00"))
    assert product.max_amount == Money(Decimal("500000.00"))
    assert product.interest_rate == Decimal("18.50")
    assert product.min_term_months == 3
    assert product.max_term_months == 36
    assert product.is_active is True


def test_application_mapper_to_domain_without_monthly_payment():
    model = make_application_model()
    aggregate = ApplicationMapper.to_domain(model)
    assert aggregate.id == 7
    assert aggregate.user_id == 42
    assert aggregate.amount == Money(Decimal("100000.00"))
    assert aggregate.term.months == 12
    assert aggregate.status == ApplicationStatus.DRAFT
    assert aggregate.monthly_payment is None


def test_application_mapper_to_domain_with_monthly_payment():
    model = make_application_model(
        status="SUBMITTED", monthly_payment=Decimal("9500.00")
    )
    aggregate = ApplicationMapper.to_domain(model)
    assert aggregate.status == ApplicationStatus.SUBMITTED
    assert aggregate.monthly_payment == Money(Decimal("9500.00"))


def test_application_mapper_to_model_applies_status_and_payment():
    model = make_application_model()
    aggregate = ApplicationMapper.to_domain(model)
    aggregate.submit()

    updated = ApplicationMapper.to_model(aggregate, model)

    assert updated is model
    assert model.status == "SUBMITTED"
    assert model.monthly_payment == aggregate.monthly_payment.amount


def test_application_mapper_to_model_leaves_untracked_fields_untouched():
    model = make_application_model(purpose="Ремонт")
    aggregate = ApplicationMapper.to_domain(model)

    ApplicationMapper.to_model(aggregate, model)

    assert model.purpose == "Ремонт"
    assert model.user_id == 42
