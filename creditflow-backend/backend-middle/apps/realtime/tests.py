from decimal import Decimal

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.applications.models import CreditApplication
from apps.products.models import CreditProduct
from config.asgi import application

from .push import push_status

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


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class NotificationConsumerConnectTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ws@example.com", password="pw12345")

    async def test_valid_token_connects_and_joins_group(self):
        token = str(AccessToken.for_user(self.user))
        communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_missing_token_is_rejected_with_4001(self):
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4001)

    async def test_invalid_token_is_rejected_with_4001(self):
        communicator = WebsocketCommunicator(application, "/ws/notifications/?token=garbage")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4001)

    async def test_inactive_user_is_rejected(self):
        self.user.is_active = False
        await sync_to_async(self.user.save)(update_fields=["is_active"])
        token = str(AccessToken.for_user(self.user))
        communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4001)


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class PushStatusDeliveryTests(TransactionTestCase):
    """Doc 3 §17/AC-4: a connected client receives application_status pushes."""

    def setUp(self):
        self.user = User.objects.create_user(email="pushed@example.com", password="pw12345")
        self.product = make_product()

    async def test_connected_client_receives_application_status_event(self):
        token = str(AccessToken.for_user(self.user))
        communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        credit_application = await sync_to_async(CreditApplication.objects.create)(
            user=self.user, product=self.product, amount=Decimal("100000.00"),
            term_months=12, status="SCORING",
        )
        await sync_to_async(push_status, thread_sensitive=False)(credit_application)

        payload = await communicator.receive_json_from()
        self.assertEqual(payload["event"], "application_status")
        self.assertEqual(payload["application_id"], credit_application.id)
        self.assertEqual(payload["status"], "SCORING")

        await communicator.disconnect()

    async def test_other_users_do_not_receive_the_push(self):
        other = await sync_to_async(User.objects.create_user)(
            email="bystander@example.com", password="pw12345"
        )
        token = str(AccessToken.for_user(other))
        communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        credit_application = await sync_to_async(CreditApplication.objects.create)(
            user=self.user, product=self.product, amount=Decimal("100000.00"),
            term_months=12, status="SCORING",
        )
        await sync_to_async(push_status, thread_sensitive=False)(credit_application)

        self.assertIs(await communicator.receive_nothing(timeout=0.2), True)
        await communicator.disconnect()
