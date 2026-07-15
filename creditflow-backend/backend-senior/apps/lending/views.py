from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import HasPermission
from lending.infrastructure.di import container as lending_container

from .models import Loan
from .permissions import IsOwner
from .serializers import LoanSerializer, RepaySerializer


class LoanViewSet(viewsets.ReadOnlyModelViewSet):
    """Doc 3 §5.2: gated by loan.view_own — CLIENT and ADMIN alike only see their own loans."""

    permission_classes = [IsAuthenticated, HasPermission, IsOwner]
    required_permission = "loan.view_own"
    serializer_class = LoanSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Loan.objects.none()
        return (
            Loan.objects.filter(user=self.request.user)
            .select_related("application")
            .prefetch_related("schedule_items", "transactions")
            .order_by("-disbursed_at")
        )

    @action(detail=True, methods=["post"])
    def repay(self, request, pk=None):
        loan = self.get_object()
        serializer = RepaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = lending_container.repay_loan().execute(
            loan.id,
            serializer.validated_data["amount"],
            serializer.validated_data["idempotency_key"],
            actor=request.user,
            request=request,
        )
        # repay() re-fetches the loan without the list/detail prefetches; reload
        # here so the response doesn't trigger extra per-relation queries.
        loan = self.get_queryset().get(id=loan.id)
        return Response(LoanSerializer(loan).data)
