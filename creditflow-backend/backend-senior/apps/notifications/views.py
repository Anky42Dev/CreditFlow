from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import NotificationFilter
from .models import Notification
from .permissions import IsOwner
from .serializers import NotificationSerializer

UNREAD_COUNT_CACHE_KEY = "unread:{user_id}"


def _unread_count(user) -> int:
    """Doc 3 §8: cached with no TTL, invalidated on read/read-all/new notification."""
    key = UNREAD_COUNT_CACHE_KEY.format(user_id=user.id)
    count = cache.get(key)
    if count is None:
        count = Notification.objects.filter(user=user, is_read=False).count()
        cache.set(key, count, None)
    return count


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Doc 3 §11: owner-based access only — every user sees just their own
    notifications, no RBAC permission required."""

    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = NotificationFilter
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
            cache.delete(UNREAD_COUNT_CACHE_KEY.format(user_id=request.user.id))
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        if updated:
            cache.delete(UNREAD_COUNT_CACHE_KEY.format(user_id=request.user.id))
        return Response({"updated": updated})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread_count": _unread_count(request.user)})
