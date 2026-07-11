from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.applications.models import CreditApplication
from apps.applications.services import approve_application, reject_application, request_documents
from apps.products.models import CreditProduct
from apps.products.services import invalidate_product_cache
from apps.rbac.models import Role
from apps.rbac.services import assign_role
from common.audit import audit_log
from common.permissions import HasPermission

from .filters import AdminApplicationFilter, AdminUserFilter
from .serializers import (
    AdminApplicationDetailSerializer,
    AdminApplicationListSerializer,
    AdminCreditProductSerializer,
    AdminUserSerializer,
    ApproveApplicationSerializer,
    ChangeUserRoleSerializer,
    RejectApplicationSerializer,
)


class AdminCreditProductViewSet(viewsets.ModelViewSet):
    """Doc 3 §10: ADMIN-only product management, including inactive products."""

    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "product.manage"
    serializer_class = AdminCreditProductSerializer
    queryset = CreditProduct.objects.all().order_by("-created_at")
    http_method_names = ["get", "post", "put", "delete", "head", "options"]

    def perform_create(self, serializer):
        instance = serializer.save()
        invalidate_product_cache(instance.id)
        audit_log(self.request.user, "product.created", instance, request=self.request)

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_product_cache(instance.id)
        audit_log(
            self.request.user,
            "product.updated",
            instance,
            changes=serializer.validated_data,
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        """Doc 3 §10: soft delete — deactivates instead of removing the row."""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        invalidate_product_cache(instance.id)
        audit_log(request.user, "product.deleted", instance, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """Doc 3 §10: SUPPORT/UNDERWRITER/ADMIN application queue and decisions.

    List/retrieve need application.view_all; approve/reject need the matching
    application.approve/application.reject permission; request-documents is
    gated by view_all since it isn't itself a credit decision.
    """

    permission_classes = [IsAuthenticated, HasPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = AdminApplicationFilter
    ordering_fields = ["created_at", "amount", "status", "submitted_at"]
    ordering = ["-created_at"]
    search_fields = ["user__email", "purpose"]

    def get_permissions(self):
        action_permission = {
            "approve": "application.approve",
            "reject": "application.reject",
            "request_documents": "application.view_all",
        }
        self.required_permission = action_permission.get(self.action, "application.view_all")
        return [IsAuthenticated(), HasPermission()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CreditApplication.objects.none()
        qs = CreditApplication.objects.select_related(
            "user", "user__profile", "product", "scoring_result"
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("documents")
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AdminApplicationDetailSerializer
        return AdminApplicationListSerializer

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        application = self.get_object()
        serializer = ApproveApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approve_application(
            application,
            comment=serializer.validated_data["comment"],
            actor=request.user,
            request=request,
        )
        application.refresh_from_db()
        return Response(AdminApplicationDetailSerializer(application).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        application = self.get_object()
        serializer = RejectApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reject_application(
            application,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            request=request,
        )
        application.refresh_from_db()
        return Response(AdminApplicationDetailSerializer(application).data)

    @action(detail=True, methods=["post"], url_path="request-documents")
    def request_documents(self, request, pk=None):
        application = self.get_object()
        request_documents(application)
        return Response(AdminApplicationDetailSerializer(application).data)


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Doc 3 §10: ADMIN-only user directory + role changes."""

    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "user.manage"
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().order_by("-created_at")
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = AdminUserFilter
    search_fields = ["email"]
    ordering_fields = ["created_at", "email", "role"]

    @action(detail=True, methods=["patch"], url_path="role")
    def role(self, request, pk=None):
        user = self.get_object()
        serializer = ChangeUserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_code = serializer.validated_data["role"]

        try:
            assign_role(user, role_code, actor=request.user, request=request)
        except Role.DoesNotExist:
            raise ValidationError({"role": [f"Unknown role code: {role_code}"]})

        user.refresh_from_db()
        return Response(AdminUserSerializer(user).data)
