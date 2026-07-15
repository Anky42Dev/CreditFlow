import re
from datetime import date

from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from common.permissions import get_user_permissions

from .models import Profile, User

PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")


class RegisterSerializer(serializers.Serializer):
    """DOC 0 §6.2: POST /auth/register {email, password} -> 201 {user}."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return User.objects.normalize_email(value)

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class UserSerializer(serializers.ModelSerializer):
    """Doc 4 §3: GET /auth/me includes the resolved RBAC permission codes so
    the frontend can gate UI without re-deriving role -> permission mapping.
    """

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "permissions"]
        read_only_fields = fields

    def get_permissions(self, obj):
        return sorted(get_user_permissions(obj))


class ProfileSerializer(serializers.ModelSerializer):
    """DOC 0 §6.2/§6.3, task step 0: merges current-user data with the profile
    (GET /profile -> user + profile; PUT /profile -> updates profile fields only).
    """

    id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "email",
            "role",
            "first_name",
            "last_name",
            "birth_date",
            "phone",
            "monthly_income",
            "avatar",
        ]
        read_only_fields = ["id", "email", "role", "avatar"]

    def validate_birth_date(self, value):
        if value is None:
            return value
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise serializers.ValidationError("Must be at least 18 years old")
        return value

    def validate_monthly_income(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Must be greater than or equal to 0")
        return value

    def validate_phone(self, value):
        if value and not PHONE_REGEX.match(value):
            raise serializers.ValidationError("Invalid phone format")
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField()


class AvatarSerializer(serializers.Serializer):
    """DOC 5 §9, Roadmap Этап 5 п.13: the resize runs in a background Celery
    task, so the upload response only confirms it was queued — the final
    avatar URL arrives via WS push (event `avatar_updated`), not here."""

    status = serializers.CharField()
