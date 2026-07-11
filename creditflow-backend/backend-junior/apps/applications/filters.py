import django_filters as df

from .models import CreditApplication


class ApplicationFilter(df.FilterSet):
    min_amount = df.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = df.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = CreditApplication
        fields = ["status", "product"]
