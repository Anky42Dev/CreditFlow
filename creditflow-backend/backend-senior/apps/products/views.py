from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .filters import CreditProductFilter
from .models import CreditProduct
from .serializers import CreditProductSerializer
from .services import get_active_products, get_product_detail


class CreditProductViewSet(ReadOnlyModelViewSet):
    """Doc 3 §8: plain, unfiltered reads of active products are served from
    the Redis cache (products:active / product:{id}); anything staff-only or
    filtered/searched/sorted falls back to a normal DB query."""

    serializer_class = CreditProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = CreditProductFilter
    ordering_fields = ["interest_rate", "max_amount", "min_amount", "created_at"]
    ordering = ["-created_at"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        qs = CreditProduct.objects.all()
        user = self.request.user
        if not (user and user.is_authenticated and user.is_staff):
            qs = qs.filter(is_active=True)
        return qs

    def _is_staff_view(self):
        user = self.request.user
        return bool(user and user.is_authenticated and user.is_staff)

    def list(self, request, *args, **kwargs):
        if self._is_staff_view() or request.query_params:
            return super().list(request, *args, **kwargs)

        data = get_active_products()
        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        if self._is_staff_view():
            return super().retrieve(request, *args, **kwargs)

        data = get_product_detail(kwargs.get("pk"))
        if data is None or not data.get("is_active"):
            raise Http404
        return Response(data)
