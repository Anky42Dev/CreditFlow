from decimal import Decimal

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CreditApplication
from apps.applications.services import calc_annuity, perform_scoring
from apps.products.models import CreditProduct
from apps.rbac.services import assign_role
from common.exceptions import ConflictError

from .models import Loan, PaymentScheduleItem, Transaction
from .services import build_payment_schedule, disburse_loan, repay

CELERY_EAGER = {"CELERY_TASK_ALWAYS_EAGER": True, "CELERY_TASK_EAGER_PROPAGATES": True}
TEST_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}
# perform_scoring calls push_status (Doc 3 §7.3); use an in-memory channel
# layer so LoanAPITests doesn't require a real Redis instance.
TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def make_product(**overrides):
    defaults = dict(
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
    return CreditProduct.objects.create(**defaults)


def make_user_with_profile(email, monthly_income=None, birth_date=None):
    user = User.objects.create_user(email=email, password="pw12345")
    profile = user.profile
    profile.monthly_income = monthly_income
    profile.birth_date = birth_date
    profile.save()
    return user


def make_approved_application(product, email, amount=Decimal("200000.00"), term_months=12):
    user = make_user_with_profile(email, monthly_income=Decimal("100000.00"), birth_date="1990-01-01")
    application = CreditApplication.objects.create(
        user=user, product=product, amount=amount, term_months=term_months,
    )
    application.monthly_payment = calc_annuity(amount, product.interest_rate, term_months)
    application.save()
    return application


class DisburseLoanTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.application = make_approved_application(self.product, "borrower@example.com")

    def test_creates_loan_schedule_and_disbursement_transaction(self):
        loan = disburse_loan(self.application)

        self.assertEqual(loan.status, "ACTIVE")
        self.assertEqual(loan.outstanding_balance, self.application.amount)
        self.assertEqual(loan.schedule_items.count(), 12)
        txn = loan.transactions.get()
        self.assertEqual(txn.type, "DISBURSEMENT")
        self.assertEqual(txn.amount, loan.principal)
        self.assertEqual(txn.balance_after, loan.principal)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "DISBURSED")

    def test_schedule_fully_amortizes_principal(self):
        loan = disburse_loan(self.application)
        total_principal = sum(
            item.principal_part for item in loan.schedule_items.all()
        )
        self.assertEqual(total_principal, loan.principal)

    def test_is_idempotent_against_retry(self):
        loan_first = disburse_loan(self.application)
        loan_second = disburse_loan(self.application)

        self.assertEqual(loan_first.id, loan_second.id)
        self.assertEqual(Loan.objects.filter(application=self.application).count(), 1)
        self.assertEqual(Transaction.objects.filter(loan=loan_first).count(), 1)


class BuildPaymentScheduleTests(TestCase):
    def test_last_installment_absorbs_rounding_drift(self):
        product = make_product()
        application = make_approved_application(product, "drift@example.com")
        loan = Loan.objects.create(
            application=application, user=application.user,
            principal=application.amount, interest_rate=product.interest_rate,
            term_months=application.term_months, monthly_payment=application.monthly_payment,
            outstanding_balance=application.amount, status="ACTIVE",
            disbursed_at=timezone.now(),
        )

        build_payment_schedule(loan)

        items = list(PaymentScheduleItem.objects.filter(loan=loan).order_by("sequence"))
        self.assertEqual(len(items), loan.term_months)
        running_balance = loan.principal
        for item in items:
            running_balance -= item.principal_part
        self.assertEqual(running_balance, Decimal("0.00"))


@override_settings(**CELERY_EAGER)
class RepayServiceTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.application = make_approved_application(self.product, "repayer@example.com")
        self.loan = disburse_loan(self.application)

    def test_reduces_balance_and_marks_nearest_pending_item_paid(self):
        first_due = self.loan.schedule_items.order_by("sequence").first()

        updated = repay(self.loan, self.loan.monthly_payment, "key-1")

        self.assertEqual(
            updated.outstanding_balance, self.loan.principal - self.loan.monthly_payment
        )
        first_due.refresh_from_db()
        self.assertEqual(first_due.status, "PAID")
        self.assertIsNotNone(first_due.paid_at)

    def test_duplicate_idempotency_key_raises_conflict_without_double_crediting(self):
        repay(self.loan, self.loan.monthly_payment, "key-dup")
        balance_after_first = Loan.objects.get(id=self.loan.id).outstanding_balance

        with self.assertRaises(ConflictError):
            repay(self.loan, self.loan.monthly_payment, "key-dup")

        self.loan.refresh_from_db()
        self.assertEqual(self.loan.outstanding_balance, balance_after_first)
        self.assertEqual(Transaction.objects.filter(idempotency_key="key-dup").count(), 1)

    def test_closes_loan_when_balance_reaches_zero(self):
        updated = repay(self.loan, self.loan.principal, "key-full")

        self.assertEqual(updated.status, "CLOSED")
        self.assertIsNotNone(updated.closed_at)
        self.assertLessEqual(updated.outstanding_balance, Decimal("0.00"))
        self.assertEqual(
            PaymentScheduleItem.objects.filter(loan=updated, status="PENDING").count(), 0
        )

    def test_repay_on_closed_loan_raises_conflict(self):
        repay(self.loan, self.loan.principal, "key-close")

        with self.assertRaises(ConflictError):
            repay(self.loan, Decimal("100.00"), "key-after-close")


@override_settings(**CELERY_EAGER, CACHES=TEST_CACHES, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class LoanAPITests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_rbac")

        self.product = make_product()
        self.application = make_approved_application(self.product, "apiborrower@example.com")
        perform_scoring(self.application.id)
        self.application.refresh_from_db()
        self.loan = self.application.loan
        self.user = self.application.user
        assign_role(self.user, "CLIENT")

        self.other_user = make_user_with_profile("other@example.com")
        assign_role(self.other_user, "CLIENT")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_only_returns_own_loans(self):
        r = self.client.get("/api/v1/loans")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)

        other_client = APIClient()
        other_client.force_authenticate(user=self.other_user)
        r = other_client.get("/api/v1/loans")
        self.assertEqual(r.data["count"], 0)

    def test_retrieve_includes_schedule_and_transactions(self):
        r = self.client.get(f"/api/v1/loans/{self.loan.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["schedule_items"]), 12)
        self.assertEqual(len(r.data["transactions"]), 1)

    def test_repay_endpoint_reduces_balance(self):
        r = self.client.post(
            f"/api/v1/loans/{self.loan.id}/repay",
            {"amount": str(self.loan.monthly_payment), "idempotency_key": "api-key-1"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            Decimal(r.data["outstanding_balance"]), self.loan.principal - self.loan.monthly_payment
        )

    def test_repay_endpoint_duplicate_key_returns_409(self):
        payload = {"amount": str(self.loan.monthly_payment), "idempotency_key": "api-key-dup"}
        self.client.post(f"/api/v1/loans/{self.loan.id}/repay", payload)
        r = self.client.post(f"/api/v1/loans/{self.loan.id}/repay", payload)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["error"]["code"], "DUPLICATE")

    def test_other_user_cannot_repay_or_view_loan(self):
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_user)
        r = other_client.get(f"/api/v1/loans/{self.loan.id}")
        self.assertEqual(r.status_code, 404)

        r = other_client.post(
            f"/api/v1/loans/{self.loan.id}/repay",
            {"amount": str(self.loan.monthly_payment), "idempotency_key": "other-user-key"},
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Transaction.objects.filter(idempotency_key="other-user-key").count(), 0)

    def test_repay_rejects_non_positive_amount(self):
        r = self.client.post(
            f"/api/v1/loans/{self.loan.id}/repay",
            {"amount": "0.00", "idempotency_key": "api-key-invalid"},
        )
        self.assertEqual(r.status_code, 400)
