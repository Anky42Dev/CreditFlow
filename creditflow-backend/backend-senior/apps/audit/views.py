from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from common.pagination import AuditLogCursorPagination
from common.permissions import HasPermission

from .filters import AuditLogFilter
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(ReadOnlyModelViewSet):
    """Doc 3 §14: GET /api/v1/admin/audit-log, gated by audit.view (ADMIN only, DOC 3 §5.2)."""

    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "audit.view"
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AuditLogFilter
    # DOC 5 §14: keyset (cursor) pagination instead of offset — see
    # common.pagination.AuditLogCursorPagination's docstring. No
    # OrderingFilter alongside it: ordering is fixed to match AuditLog's own
    # Meta.ordering (newest first) for cursor stability.
    pagination_class = AuditLogCursorPagination
    # DOC 5 §14: AuditLog's PK is now composite (id, created_at) — see
    # apps.audit.models.AuditLog's docstring — so DRF's default lookup
    # (`.filter(pk=<url kwarg>)`) breaks for the detail route (`pk` requires
    # a tuple, not a single value). Look up by `id` instead, which stays a
    # plain, single-value field.
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AuditLog.objects.none()
        # DOC 5 §14: this is the "heavy admin analytics" read path — the one
        # place that actually goes to the read replica (config/db_router.py
        # explains why this is opt-in, not app-wide router-level routing).
        return AuditLog.objects.using("replica").select_related("actor").all()
