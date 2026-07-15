from decimal import Decimal

from rest_framework import serializers

from .models import Loan, PaymentScheduleItem, Transaction


class PaymentScheduleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentScheduleItem
        fields = [
            "id", "sequence", "due_date", "amount", "principal_part",
            "interest_part", "status", "paid_at",
        ]
        read_only_fields = fields


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "type", "amount", "balance_after", "created_at"]
        read_only_fields = fields


class LoanSerializer(serializers.ModelSerializer):
    schedule_items = PaymentScheduleItemSerializer(many=True, read_only=True)
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id", "application", "principal", "interest_rate", "term_months",
            "monthly_payment", "outstanding_balance", "status", "disbursed_at",
            "closed_at", "schedule_items", "transactions",
        ]
        read_only_fields = fields


class RepaySerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    idempotency_key = serializers.CharField(max_length=64)
