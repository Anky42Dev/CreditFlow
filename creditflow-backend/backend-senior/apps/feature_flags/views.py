"""DOC 5 §11: admin API for feature flags. Not a ModelViewSet — flags are
Redis-keyed by name, not Django ORM rows — so this is a pair of plain
APIViews mirroring apps.adminpanel's HasPermission-gated pattern.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasPermission

from .serializers import FeatureFlagWriteSerializer
from .services import audit_flag_change, delete_flag, get_flag, list_flags, set_flag


class FeatureFlagListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "feature_flag.manage"

    def get(self, request):
        flags = list_flags()
        data = [{"name": name, **cfg} for name, cfg in sorted(flags.items())]
        return Response(data)


class FeatureFlagDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "feature_flag.manage"

    def get(self, request, name):
        cfg = get_flag(name)
        if cfg is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response({"name": name, **cfg})

    def put(self, request, name):
        serializer = FeatureFlagWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before = get_flag(name)
        after = set_flag(
            name,
            global_=serializer.validated_data["is_global"],
            percentage=serializer.validated_data["percentage"],
        )
        audit_flag_change(request.user, name, before, after, request)
        return Response({"name": name, **after})

    def delete(self, request, name):
        before = get_flag(name)
        if before is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        delete_flag(name)
        audit_flag_change(request.user, name, before, None, request)
        return Response(status=status.HTTP_204_NO_CONTENT)
