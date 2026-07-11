from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.lending.models import Loan, PaymentScheduleItem
from apps.products.models import CreditProduct

from .models import CreditApplication, ScoringResult
from .services import calc_annuity, compute_score, perform_scoring, submit_application, underwriter_queue_queryset

CELERY_EAGER = {"CELERY_TASK_ALWAYS_EAGER": True, "CELERY_TASK_EAGER_PROPAGATES": True}
# perform_scoring now calls push_status (Doc 3 §7.3), which needs a channel layer;
# swap in-memory so these tests don't require a real Redis instance.
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


class CalcAnnuityTests(TestCase):
    def test_returns_expected_payment(self):
        payment = calc_annuity(Decimal("100000"), Decimal("12"), 12)
        self.assertTrue(Decimal("8800") < payment < Decimal("8900"))

    def test_zero_rate_splits_evenly(self):
        payment = calc_annuity(Decimal("120000"), Decimal("0"), 12)
        self.assertEqual(payment, Decimal("10000.00"))


class ProfileAutoCreationTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(email="new@example.com", password="pw12345")
        self.assertTrue(hasattr(user, "profile"))


class ComputeScoreMissingProfileTests(TestCase):
    """Guards against the signal-failure/stuck-SCORING scenario from code review."""

    def test_missing_profile_degrades_to_missing_data_instead_of_raising(self):
        user = User.objects.create_user(email="noprofile@example.com", password="pw12345")
        user.profile.delete()
        product = make_product()
        application = CreditApplication.objects.create(
            user=user, product=product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("18000.00"),
        )
        self.assertEqual(compute_score(application), 400)


class ComputeScoreTests(TestCase):
    def setUp(self):
        self.product = make_product()

    def test_high_income_low_ratio_scores_high(self):
        user = make_user_with_profile("rich@example.com", monthly_income=Decimal("100000.00"), birth_date="1990-01-01")
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("18000.00"),
        )
        self.assertEqual(compute_score(application), 800)

    def test_missing_income_and_birth_date_scores_low(self):
        user = make_user_with_profile("poor@example.com")
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("18000.00"),
        )
        self.assertEqual(compute_score(application), 400)


@override_settings(**CELERY_EAGER, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class PerformScoringTests(TestCase):
    def setUp(self):
        self.product = make_product()

    def test_approves_with_sufficient_income(self):
        user = make_user_with_profile("approved@example.com", monthly_income=Decimal("100000.00"), birth_date="1990-01-01")
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
        )
        application.monthly_payment = calc_annuity(application.amount, self.product.interest_rate, 12)
        application.save()

        result = perform_scoring(application.id)

        self.assertEqual(result.status, "DISBURSED")
        self.assertEqual(result.scoring_result.decision, "APPROVED")
        self.assertTrue(Loan.objects.filter(application=application).exists())

    def test_manual_review_for_borderline_score(self):
        user = make_user_with_profile("borderline@example.com", monthly_income=Decimal("50000.00"), birth_date="1990-01-01")
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("15000.00"),  # ratio 0.3 -> +100 -> score 600
        )

        result = perform_scoring(application.id)

        self.assertEqual(result.status, "MANUAL_REVIEW")
        self.assertEqual(ScoringResult.objects.get(application=application).decision, "MANUAL_REVIEW")

    def test_rejects_with_missing_income_data(self):
        user = make_user_with_profile("rejected@example.com")
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("18000.00"),
        )

        result = perform_scoring(application.id)

        self.assertEqual(result.status, "REJECTED")

    def test_intermediate_status_is_scoring_before_decision(self):
        """The task always passes through SCORING, matching Doc 3 §6.3's state machine."""
        user = make_user_with_profile("mid@example.com", monthly_income=Decimal("100000.00"), birth_date="1990-01-01")
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("18000.00"),
        )
        self.assertNotEqual(application.status, "SCORING")
        perform_scoring(application.id)
        application.refresh_from_db()
        self.assertIn(application.status, ("DISBURSED", "MANUAL_REVIEW", "REJECTED"))


class SubmitApplicationServiceTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.user = make_user_with_profile("submitter@example.com", monthly_income=Decimal("100000.00"), birth_date="1990-01-01")

    @override_settings(**CELERY_EAGER, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
    def test_submit_queues_scoring_synchronously_in_eager_mode(self):
        application = CreditApplication.objects.create(
            user=self.user, product=self.product, amount=Decimal("200000.00"), term_months=12,
        )
        submit_application(application)
        application.refresh_from_db()
        self.assertIn(application.status, ("DISBURSED", "MANUAL_REVIEW", "REJECTED"))
        self.assertIsNotNone(application.monthly_payment)

    def test_submit_non_draft_raises_conflict(self):
        application = CreditApplication.objects.create(
            user=self.user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            status="SUBMITTED",
        )
        from common.exceptions import ConflictError

        with self.assertRaises(ConflictError):
            submit_application(application)

    def test_submit_does_not_score_synchronously_without_eager_mode(self):
        """Doc 3 §18: scoring in the synchronous request path is a defect — submit only enqueues."""
        application = CreditApplication.objects.create(
            user=self.user, product=self.product, amount=Decimal("200000.00"), term_months=12,
        )
        with mock.patch("apps.applications.tasks.score_application.delay") as delay:
            result = submit_application(application)
        delay.assert_called_once_with(application.id)
        self.assertEqual(result.status, "SUBMITTED")


@override_settings(**CELERY_EAGER, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class CreditApplicationAPITests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.user = make_user_with_profile("apiuser@example.com", monthly_income=Decimal("100000.00"), birth_date="1990-01-01")
        self.other_user = make_user_with_profile("other@example.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_application_draft(self):
        r = self.client.post(
            "/api/v1/credit-applications",
            {"product": self.product.id, "amount": "200000.00", "term_months": 12, "purpose": "Ремонт"},
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["status"], "DRAFT")

    def test_list_only_returns_own_applications(self):
        self.client.post(
            "/api/v1/credit-applications",
            {"product": self.product.id, "amount": "200000.00", "term_months": 12},
        )
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_user)
        r = other_client.get("/api/v1/credit-applications")
        self.assertEqual(r.data["count"], 0)

    def test_submit_moves_through_async_scoring_and_returns_decision(self):
        created = self.client.post(
            "/api/v1/credit-applications",
            {"product": self.product.id, "amount": "200000.00", "term_months": 12},
        )
        app_id = created.data["id"]
        r = self.client.post(f"/api/v1/credit-applications/{app_id}/submit")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "DISBURSED")
        self.assertEqual(r.data["scoring_result"]["decision"], "APPROVED")
        self.assertTrue(Loan.objects.filter(application_id=app_id).exists())
        self.assertEqual(PaymentScheduleItem.objects.filter(loan__application_id=app_id).count(), 12)

    def test_submit_non_draft_returns_409(self):
        created = self.client.post(
            "/api/v1/credit-applications",
            {"product": self.product.id, "amount": "200000.00", "term_months": 12},
        )
        app_id = created.data["id"]
        self.client.post(f"/api/v1/credit-applications/{app_id}/submit")
        r = self.client.post(f"/api/v1/credit-applications/{app_id}/submit")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["error"]["code"], "CONFLICT")

    def test_update_non_draft_returns_409(self):
        created = self.client.post(
            "/api/v1/credit-applications",
            {"product": self.product.id, "amount": "200000.00", "term_months": 12},
        )
        app_id = created.data["id"]
        self.client.post(f"/api/v1/credit-applications/{app_id}/submit")
        r = self.client.put(
            f"/api/v1/credit-applications/{app_id}",
            {"amount": "250000.00", "term_months": 24},
        )
        self.assertEqual(r.status_code, 409)


@override_settings(**CELERY_EAGER, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class PerformScoringAuditLogTests(TestCase):
    """Doc 3 §14: every status transition of perform_scoring is audited."""

    def setUp(self):
        self.product = make_product()

    def test_status_change_is_logged_with_before_after(self):
        user = make_user_with_profile(
            "audited@example.com", monthly_income=Decimal("100000.00"), birth_date="1990-01-01"
        )
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("18000.00"), status="SUBMITTED",
        )

        perform_scoring(application.id)

        entries = AuditLog.objects.filter(
            action="application.status_changed", object_type="CreditApplication", object_id=application.id
        ).order_by("id")
        self.assertEqual(entries.count(), 2)
        self.assertEqual(entries[0].changes, {"before": "SUBMITTED", "after": "SCORING"})
        self.assertEqual(entries[1].changes["before"], "SCORING")
        self.assertIsNone(entries[0].actor)

    def test_disbursement_writes_its_own_audit_entry(self):
        user = make_user_with_profile(
            "disbursed-audit@example.com", monthly_income=Decimal("100000.00"), birth_date="1990-01-01"
        )
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
            monthly_payment=Decimal("18000.00"), status="SUBMITTED",
        )

        perform_scoring(application.id)

        self.assertTrue(AuditLog.objects.filter(action="loan.disbursed").exists())


class UnderwriterQueueNPlusOneTests(TestCase):
    """Doc 3 §13.1/§13.2: N+1 regression guard for the future underwriter dashboard queryset."""

    def setUp(self):
        self.product = make_product()
        for i in range(5):
            user = make_user_with_profile(
                f"queue{i}@example.com", monthly_income=Decimal("50000.00"), birth_date="1990-01-01"
            )
            CreditApplication.objects.create(
                user=user, product=self.product, amount=Decimal("100000.00"), term_months=12,
                monthly_payment=Decimal("9000.00"), status="MANUAL_REVIEW",
            )

    def test_iterating_queue_does_not_trigger_per_row_queries(self):
        qs = underwriter_queue_queryset()
        # 1 query for the annotated queryset itself; accessing select_related
        # fields (user, user.profile, product) must not add more.
        with self.assertNumQueries(1):
            rows = list(qs)
            for row in rows:
                _ = row.user.email
                _ = row.user.profile.monthly_income
                _ = row.product.name
                _ = row.waiting_hours
