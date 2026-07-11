from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(user_id):
    User = get_user_model()
    try:
        return User.objects.get(**{api_settings.USER_ID_FIELD: user_id}, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Doc 3 §7.2: authenticates the WS handshake via ?token=<access>.

    Runs before routing so `scope["user"]` is populated (or AnonymousUser)
    by the time NotificationConsumer.connect() checks it.
    """

    async def __call__(self, scope, receive, send):
        scope["user"] = await self._authenticate(scope)
        return await super().__call__(scope, receive, send)

    async def _authenticate(self, scope):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        if not token:
            return AnonymousUser()

        try:
            access = AccessToken(token)
        except TokenError:
            return AnonymousUser()

        user_id = access.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            return AnonymousUser()

        return await _get_user(user_id)
