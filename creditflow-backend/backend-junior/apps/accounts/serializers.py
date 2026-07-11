import re
from datetime import date

from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Profile, User

PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")


class RegisterSerializer(serializers.Serializer):
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
    class Meta:
        model = User
        fields = ["id", "email", "role"]
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "first_name",
            "last_name",
            "birth_date",
            "phone",
            "monthly_income",
            "avatar",
        ]
        read_only_fields = ["id", "avatar"]

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
    avatar = serializers.CharField()
