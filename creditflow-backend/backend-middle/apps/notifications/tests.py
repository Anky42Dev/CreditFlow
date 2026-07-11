from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CreditApplication
from apps.applications.services import calc_annuity
from apps.lending.services import disburse_loan
from apps.lending.tasks import mark_overdue_payments
from apps.products.models import CreditProduct

from .models import Notification
from .services import notify_user
from .tasks import build_email, send_due_reminders, send_email_async
from .views import UNREAD_COUNT_CACHE_KEY

CELERY_EAGER = {"CELERY_TASK_ALWAYS_EAGER": True, "CELERY_TASK_EAGER_PROPAGATES": True}
TEST_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
# notify_user calls push_notification (Doc 3 §7.3/§11); use an in-memory
# channel layer so these tests don't require a real Redis instance.
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


def make_user(email):
    return User.objects.create_user(email=email, password="pw12345")


def make_approved_application(product, email, amount=Decimal("200000.00"), term_months=12):
    user = make_user(email)
    application = CreditApplication.objects.create(user=user, product=product, amount=amount, term_months=term_months)
    application.monthly_payment = calc_annuity(amount, product.interest_rate, term_months)
    application.save()
    return application


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, CACHES=TEST_CACHES, **CELERY_EAGER)
class NotifyUserServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.product = make_product()
        self.application = make_approved_application(self.product, "notify@example.com")

    def test_creates_notification_with_rendered_title_and_body(self):
        notification = notify_user(self.application.user, "application.approved", self.application)

        self.assertEqual(notification.title, "Заявка одобрена")
        self.assertIn(str(self.application.id), notification.body)
        self.assertFalse(notification.is_read)
        self.assertTrue(Notification.objects.filter(id=notification.id).exists())

    def test_unmapped_type_falls_back_to_generic_title_instead_of_crashing(self):
        notification = notify_user(self.application.user, "some.unknown.type", self.application)
        self.assertEqual(notification.title, "Уведомление")

    def test_queues_email_task_in_eager_mode(self):
        notify_user(self.application.user, "application.approved", self.application)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.application.user.email])

    def test_invalidates_unread_count_cache(self):
        key = UNREAD_COUNT_CACHE_KEY.format(user_id=self.application.user.id)
        cache.set(key, 41, None)
        notify_user(self.application.user, "application.approved", self.application)
        self.assertIsNone(cache.get(key))

    def test_pushes_over_websocket(self):
        with mock.patch("apps.realtime.push.push_notification") as push:
            notify_user(self.application.user, "application.approved", self.application)
        push.assert_called_once()


class BuildEmailTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.application = make_approved_application(self.product, "build@example.com")

    def test_resolves_object_and_renders_subject_body(self):
        subject, body = build_email("application.approved", self.application.id)
        self.assertEqual(subject, "Заявка одобрена")
        self.assertIn(str(self.application.id), body)

    def test_unknown_object_falls_back_to_subject_only(self):
        subject, body = build_email("application.approved", 999999)
        self.assertEqual(subject, "Заявка одобрена")
        self.assertEqual(body, subject)


@override_settings(**CELERY_EAGER)
class SendEmailAsyncTaskTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.application = make_approved_application(self.product, "task@example.com")

    def test_sends_email_via_console_backend(self):
        send_email_async.delay(self.application.user.email, "application.approved", self.application.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Заявка одобрена")


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, CACHES=TEST_CACHES, **CELERY_EAGER)
class ScoringAndDisbursementNotificationTests(TestCase):
    """Doc 3 §11: perform_scoring / disburse_loan fire notify_user on decision/disbursement."""

    def setUp(self):
        cache.clear()
        self.product = make_product()

    def test_perform_scoring_notifies_on_approval(self):
        from apps.applications.services import perform_scoring

        user = make_user("approved-notif@example.com")
        user.profile.monthly_income = Decimal("100000.00")
        user.profile.birth_date = "1990-01-01"
        user.profile.save()
        application = CreditApplication.objects.create(
            user=user, product=self.product, amount=Decimal("200000.00"), term_months=12,
        )
        application.monthly_payment = calc_annuity(application.amount, self.product.interest_rate, 12)
        application.save()

        perform_scoring(application.id)

        self.assertTrue(Notification.objects.filter(user=user, type="application.approved").exists())
        self.assertTrue(Notification.objects.filter(user=user, type="loan.disbursed").exists())

    def test_disburse_loan_is_idempotent_and_does_not_double_notify(self):
        application = make_approved_application(self.product, "idempotent@example.com")
        loan = disburse_loan(application)
        Notification.objects.all().delete()

        same_loan = disburse_loan(application)

        self.assertEqual(loan.id, same_loan.id)
        self.assertFalse(Notification.objects.filter(type="loan.disbursed").exists())


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, CACHES=TEST_CACHES, **CELERY_EAGER)
class NotificationAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("api@example.com")
        self.other_user = make_user("other-api@example.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.n1 = Notification.objects.create(user=self.user, type="t", title="A", body="a")
        self.n2 = Notification.objects.create(user=self.user, type="t", title="B", body="b", is_read=True)
        Notification.objects.create(user=self.other_user, type="t", title="C", body="c")

    def test_list_only_returns_own_notifications(self):
        r = self.client.get("/api/v1/notifications")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)

    def test_list_filters_by_is_read(self):
        r = self.client.get("/api/v1/notifications?is_read=false")
        ids = {item["id"] for item in r.data["results"]}
        self.assertEqual(ids, {self.n1.id})

    def test_read_marks_single_notification_and_invalidates_cache(self):
        cache.set(UNREAD_COUNT_CACHE_KEY.format(user_id=self.user.id), 99, None)

        r = self.client.post(f"/api/v1/notifications/{self.n1.id}/read")

        self.assertEqual(r.status_code, 200)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)
        self.assertIsNone(cache.get(UNREAD_COUNT_CACHE_KEY.format(user_id=self.user.id)))

    def test_cannot_read_other_users_notification(self):
        other_notification = Notification.objects.filter(user=self.other_user).first()
        r = self.client.post(f"/api/v1/notifications/{other_notification.id}/read")
        self.assertEqual(r.status_code, 404)

    def test_read_all_marks_every_unread_notification(self):
        r = self.client.post("/api/v1/notifications/read-all")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["updated"], 1)
        self.assertFalse(Notification.objects.filter(user=self.user, is_read=False).exists())

    def test_unread_count_computes_and_caches(self):
        r = self.client.get("/api/v1/notifications/unread-count")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["unread_count"], 1)
        self.assertEqual(cache.get(UNREAD_COUNT_CACHE_KEY.format(user_id=self.user.id)), 1)

    def test_unread_count_served_from_cache_without_recount(self):
        cache.set(UNREAD_COUNT_CACHE_KEY.format(user_id=self.user.id), 7, None)
        r = self.client.get("/api/v1/notifications/unread-count")
        self.assertEqual(r.data["unread_count"], 7)


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, CACHES=TEST_CACHES, **CELERY_EAGER)
class MarkOverduePaymentsTaskTests(TestCase):
    def setUp(self):
        cache.clear()
        self.product = make_product()

    def _make_active_loan_with_past_due_item(self, email):
        application = make_approved_application(self.product, email)
        loan = disburse_loan(application)
        item = loan.schedule_items.order_by("sequence").first()
        item.due_date = timezone.now().date() - timedelta(days=1)
        item.save(update_fields=["due_date"])
        return loan, item

    def test_marks_pending_item_and_loan_overdue_and_notifies(self):
        loan, item = self._make_active_loan_with_past_due_item("overdue@example.com")

        mark_overdue_payments()

        item.refresh_from_db()
        loan.refresh_from_db()
        self.assertEqual(item.status, "OVERDUE")
        self.assertEqual(loan.status, "OVERDUE")
        self.assertTrue(Notification.objects.filter(user=loan.user, type="payment.overdue").exists())

    def test_future_due_items_are_untouched(self):
        application = make_approved_application(self.product, "future@example.com")
        loan = disburse_loan(application)

        mark_overdue_payments()

        loan.refresh_from_db()
        self.assertEqual(loan.status, "ACTIVE")

    def test_is_a_noop_when_nothing_is_overdue(self):
        self.assertEqual(mark_overdue_payments(), 0)


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, CACHES=TEST_CACHES, **CELERY_EAGER)
class SendDueRemindersTaskTests(TestCase):
    def setUp(self):
        cache.clear()
        self.product = make_product()

    def test_notifies_borrowers_with_instalment_due_in_three_days(self):
        application = make_approved_application(self.product, "reminder@example.com")
        loan = disburse_loan(application)
        item = loan.schedule_items.order_by("sequence").first()
        item.due_date = timezone.now().date() + timedelta(days=3)
        item.save(update_fields=["due_date"])

        send_due_reminders()

        self.assertTrue(Notification.objects.filter(user=loan.user, type="payment.due").exists())

    def test_does_not_notify_for_items_due_further_out(self):
        application = make_approved_application(self.product, "farfuture@example.com")
        loan = disburse_loan(application)
        # build_payment_schedule already set due dates a month+ out; well past 3 days.
        send_due_reminders()
        self.assertFalse(Notification.objects.filter(user=loan.user, type="payment.due").exists())
