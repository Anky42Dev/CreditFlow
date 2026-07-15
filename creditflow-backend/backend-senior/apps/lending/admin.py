from django.contrib import admin

from .models import Loan, PaymentScheduleItem


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "application", "principal", "outstanding_balance", "status", "disbursed_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]


@admin.register(PaymentScheduleItem)
class PaymentScheduleItemAdmin(admin.ModelAdmin):
    list_display = ["id", "loan", "sequence", "due_date", "amount", "status"]
    list_filter = ["status"]


# DOC 5 §14, Roadmap Этап 5 п.14: Transaction is partitioned by month with a
# composite (id, created_at) primary key — Django admin (as of 5.2) cannot
# register models with a composite PK ("has a composite primary key, so it
# cannot be registered with admin"), so no TransactionAdmin. Read via
# apps.lending.views.LoanViewSet (nested under Loan) or the ORM/psql directly.
