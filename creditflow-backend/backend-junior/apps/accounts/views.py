from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AvatarSerializer,
    AvatarUploadSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import register_user, upload_avatar


class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfileView(RetrieveUpdateAPIView):
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
