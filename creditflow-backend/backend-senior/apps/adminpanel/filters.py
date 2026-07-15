import django_filters as df

from apps.accounts.models import User
from apps.applications.models import CreditApplication


class AdminApplicationFilter(df.FilterSet):
    """Doc 3 §13.3."""

    status = df.MultipleChoiceFilter(choices=CreditApplication.STATUS_CHOICES)
    created_from = df.DateFilter(field_name="created_at", lookup_expr="gte")
    created_to = df.DateFilter(field_name="created_at", lookup_expr="lte")
    user_email = df.CharFilter(field_name="user__email", lookup_expr="icontains")
    min_amount = df.NumberFilter(field_name="amount", lookup_expr="gte")

    class Meta:
        model = CreditApplication
        fields = ["status", "user", "created_from", "created_to", "user_email", "min_amount"]


class AdminUserFilter(df.FilterSet):
    email = df.CharFilter(field_name="email", lookup_expr="icontains")

    class Meta:
        model = User
        fields = ["email", "role", "is_active"]
