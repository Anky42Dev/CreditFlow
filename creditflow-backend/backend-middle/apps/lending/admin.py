from django.contrib import admin

from .models import Loan, PaymentScheduleItem, Transaction


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "application", "principal", "outstanding_balance", "status", "disbursed_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]


@admin.register(PaymentScheduleItem)
class PaymentScheduleItemAdmin(admin.ModelAdmin):
    list_display = ["id", "loan", "sequence", "due_date", "amount", "status"]
    list_filter = ["status"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "loan", "type", "amount", "balance_after", "created_at"]
    list_filter = ["type"]
