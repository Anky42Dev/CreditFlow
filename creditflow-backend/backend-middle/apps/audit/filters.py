import django_filters as df

from .models import AuditLog


class AuditLogFilter(df.FilterSet):
    created_from = df.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_to = df.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["actor", "action", "object_type"]
