from django.contrib import admin

from .models import CreditProduct


@admin.register(CreditProduct)
class CreditProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug", "min_amount", "max_amount", "interest_rate", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
