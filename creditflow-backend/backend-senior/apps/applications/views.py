from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.products.models import CreditProduct
from common.exceptions import ConflictError
from lending.infrastructure.di import container as lending_container

from .filters import ApplicationFilter
from .models import CreditApplication
from .permissions import IsOwner
from .serializers import (
    CreditApplicationCreateSerializer,
    CreditApplicationSerializer,
    CreditApplicationUpdateSerializer,
)


def _get_product_or_404(product_id):
    try:
        return CreditProduct.objects.get(pk=product_id)
    except (CreditProduct.DoesNotExist, ValueError, TypeError):
        raise Http404


class CreditApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ApplicationFilter
    ordering_fields = ["created_at", "amount", "status"]
    ordering = ["-created_at"]
    search_fields = ["purpose"]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CreditApplication.objects.none()
        return CreditApplication.objects.filter(user=self.request.user).select_related(
            "product", "scoring_result"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return CreditApplicationCreateSerializer
        if self.action == "update":
            return CreditApplicationUpdateSerializer
        return CreditApplicationSerializer

    def create(self, request, *args, **kwargs):
        product_id = request.data.get("product")
        if not product_id:
            raise ValidationError({"product": ["This field is required."]})
        product = _get_product_or_404(product_id)

        serializer = self.get_serializer(
            data=request.data, context={"product": product}
        )
        serializer.is_valid(raise_exception=True)
        application = CreditApplication.objects.create(
            user=request.user, product=product, **serializer.validated_data
        )
        out = CreditApplicationSerializer(application)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != "DRAFT":
            raise ConflictError(message="Only DRAFT applications can be edited")

        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CreditApplicationSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != "DRAFT":
            raise ConflictError(message="Only DRAFT applications can be deleted")
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        application = self.get_object()
        model = lending_container.submit_application().execute(application.id)
        return Response(CreditApplicationSerializer(model).data)
