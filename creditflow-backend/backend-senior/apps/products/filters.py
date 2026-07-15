import django_filters as df

from .models import CreditProduct


class CreditProductFilter(df.FilterSet):
    min_amount = df.NumberFilter(field_name="min_amount", lookup_expr="gte")
    max_amount = df.NumberFilter(field_name="max_amount", lookup_expr="lte")

    class Meta:
        model = CreditProduct
        fields = ["is_active"]
