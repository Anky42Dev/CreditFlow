from rest_framework import serializers

from .models import CreditApplication, Document, ScoringResult


class ScoringResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoringResult
        fields = ["score", "decision", "reason", "created_at"]
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "doc_type", "file", "uploaded_at"]
        read_only_fields = fields


class CreditApplicationSerializer(serializers.ModelSerializer):
    scoring_result = ScoringResultSerializer(read_only=True)

    class Meta:
        model = CreditApplication
        fields = [
            "id",
            "product",
            "amount",
            "term_months",
            "purpose",
            "status",
            "monthly_payment",
            "created_at",
            "updated_at",
            "submitted_at",
            "scoring_result",
        ]
        read_only_fields = fields


class CreditApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditApplication
        fields = ["amount", "term_months", "purpose"]

    def validate(self, attrs):
        product = self.context["product"]
        if not product.is_active:
            raise serializers.ValidationError({"product": ["Product is not active"]})
        if not (product.min_amount <= attrs["amount"] <= product.max_amount):
            raise serializers.ValidationError({"amount": ["Amount out of product range"]})
        if not (product.min_term_months <= attrs["term_months"] <= product.max_term_months):
            raise serializers.ValidationError({"term_months": ["Term out of product range"]})
        return attrs


class CreditApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditApplication
        fields = ["amount", "term_months", "purpose"]
        extra_kwargs = {
            "amount": {"required": False},
            "term_months": {"required": False},
        }

    def validate(self, attrs):
        product = self.instance.product
        amount = attrs.get("amount", self.instance.amount)
        term_months = attrs.get("term_months", self.instance.term_months)
        if not (product.min_amount <= amount <= product.max_amount):
            raise serializers.ValidationError({"amount": ["Amount out of product range"]})
        if not (product.min_term_months <= term_months <= product.max_term_months):
            raise serializers.ValidationError({"term_months": ["Term out of product range"]})
        return attrs
