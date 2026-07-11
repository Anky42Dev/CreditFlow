from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from .filters import CreditProductFilter
from .models import CreditProduct
from .serializers import CreditProductSerializer


class CreditProductViewSet(ReadOnlyModelViewSet):
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
