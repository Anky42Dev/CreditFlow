from rest_framework import serializers

from .models import CreditProduct


class CreditProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditProduct
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "min_amount",
            "max_amount",
            "interest_rate",
            "min_term_months",
            "max_term_months",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields
