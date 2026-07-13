from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    AvatarSerializer,
    AvatarUploadSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import register_user, upload_avatar


def _set_refresh_cookie(response, refresh_token):
    """DOC 6 §3.2: refresh lives only in an httpOnly cookie, never in JS-readable storage."""
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Strict",
        path="/api/v1/auth/",
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/v1/auth/")


def _enforce_csrf(request):
    """Double-submit check for requests authenticated via the ambient refresh cookie."""
    SessionAuthentication().enforce_csrf(request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(TokenObtainPairView):
    """DOC 0 §6.1 login, extended per DOC 6 §3: also sets refresh as httpOnly cookie.

    Body still returns {access, refresh} unchanged for backward compatibility
    with Junior/Middle clients that keep using body-based refresh.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = response.data.get("refresh")
        if refresh:
            _set_refresh_cookie(response, refresh)
        return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RefreshView(TokenRefreshView):
    """DOC 6 §3.2 silent refresh: falls back to the httpOnly cookie when the
    request body has no `refresh` field. The legacy body-based flow (Junior/
    Middle) is untouched and CSRF-exempt, since the client already holds a
    token an attacker cannot forge. The cookie-driven path requires a valid
    CSRF header, since the cookie is sent automatically by the browser.
    """

    def post(self, request, *args, **kwargs):
        body_refresh = request.data.get("refresh") if hasattr(request.data, "get") else None
        if body_refresh:
            return super().post(request, *args, **kwargs)

        cookie_refresh = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not cookie_refresh:
            raise InvalidToken("No refresh token provided.")
        _enforce_csrf(request)

        serializer = self.get_serializer(data={"refresh": cookie_refresh})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """DOC 6 §3: clears the httpOnly refresh cookie. CSRF-protected since it
    is only meaningful when the ambient cookie is present.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        if request.COOKIES.get(settings.REFRESH_COOKIE_NAME):
            _enforce_csrf(request)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class RegisterView(APIView):
    """DOC 0 §6.2: POST /auth/register {email, password} -> 201 {user}."""

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    """DOC 1 §auth: GET /auth/me -> 200 {id, email, role} for the authenticated user."""

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileView(RetrieveUpdateAPIView):
    """DOC 0 §6.2, task step 0: GET returns current user + profile data;
    PUT updates profile fields only (ФИО, дата рождения, доход, телефон).
    """

    serializer_class = ProfileSerializer
    http_method_names = ["get", "put", "head", "options"]

    def get_object(self):
        return self.request.user.profile


class AvatarUploadView(APIView):
    serializer_class = AvatarUploadSerializer

    @extend_schema(request=AvatarUploadSerializer, responses={200: AvatarSerializer})
    def post(self, request):
        file = request.FILES.get("avatar")
        if not file:
            raise ValidationError({"avatar": ["This field is required."]})
        profile = upload_avatar(request.user.profile, file)
        return Response({"avatar": profile.avatar.url})
