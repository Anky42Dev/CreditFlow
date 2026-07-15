# DOC 5 §14, Roadmap Этап 5 п.14: AuditLog is partitioned by month with a
# composite (id, created_at) primary key — Django admin (as of 5.2) cannot
# register models with a composite PK ("has a composite primary key, so it
# cannot be registered with admin"). Read via GET /api/v1/admin/audit-log
# (apps.audit.views.AuditLogViewSet) instead.
