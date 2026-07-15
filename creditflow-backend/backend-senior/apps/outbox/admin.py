from django.contrib import admin

from .models import OutboxMessage


@admin.register(OutboxMessage)
class OutboxMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "aggregate_id", "published", "created_at", "published_at")
    list_filter = ("event_type", "published")
    readonly_fields = [f.name for f in OutboxMessage._meta.fields]
