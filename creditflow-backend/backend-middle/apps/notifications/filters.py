import django_filters as df

from .models import Notification


class NotificationFilter(df.FilterSet):
    class Meta:
        model = Notification
        fields = ["is_read"]
