from django.contrib import admin

from .models import CreditApplication, Document, ScoringResult


@admin.register(CreditApplication)
class CreditApplicationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "product", "amount", "term_months", "status", "created_at"]
    list_filter = ["status", "product"]
    search_fields = ["user__email", "purpose"]


@admin.register(ScoringResult)
class ScoringResultAdmin(admin.ModelAdmin):
    list_display = ["id", "application", "score", "decision", "created_at"]
    list_filter = ["decision"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["id", "application", "doc_type", "uploaded_at"]
    list_filter = ["doc_type"]
