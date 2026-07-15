from rest_framework import serializers


class FeatureFlagWriteSerializer(serializers.Serializer):
    is_global = serializers.BooleanField(default=False)
    percentage = serializers.IntegerField(min_value=0, max_value=100, default=0)
