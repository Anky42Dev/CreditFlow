from rest_framework import serializers

from apps.accounts.models import User
from apps.applications.models import CreditApplication
from apps.applications.serializers import DocumentSerializer, ScoringResultSerializer
from apps.products.models import CreditProduct


class AdminCreditProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditProduct
        fields = [
            "id", "name", "slug", "description", "min_amount", "max_amount",
            "interest_rate", "min_term_months", "max_term_months", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AdminApplicationListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = CreditApplication
        fields = [
            "id", "user", "user_email", "product", "amount", "term_months",
            "status", "monthly_payment", "created_at", "submitted_at",
        ]
        read_only_fields = fields


class AdminApplicationDetailSerializer(serializers.ModelSerializer):
    """Doc 3 §10/§13.1: full detail incl. documents and scoring, N+1-safe via
    the viewset's select_related/prefetch_related."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    scoring_result = ScoringResultSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = CreditApplication
        fields = [
            "id", "user", "user_email", "product", "amount", "term_months", "purpose",
            "status", "monthly_payment", "created_at", "updated_at", "submitted_at",
            "scoring_result", "documents",
        ]
        read_only_fields = fields


class ApproveApplicationSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class RejectApplicationSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "role", "is_active", "is_staff", "created_at"]
        read_only_fields = fields


class ChangeUserRoleSerializer(serializers.Serializer):
    role = serializers.CharField()
