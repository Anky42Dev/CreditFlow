from rest_framework.pagination import CursorPagination, PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AuditLogCursorPagination(CursorPagination):
    """DOC 5 §14: keyset (cursor) pagination for the audit log instead of
    offset — an OFFSET-based page N on a fast-growing, append-only table
    means Postgres has to walk and discard N rows on every request, and
    "page 5" can silently skip/repeat rows if the underlying data shifts
    between requests. Cursor pagination seeks directly from an opaque
    position instead. Ordering is fixed to match AuditLog's own Meta.ordering
    (newest first) — deliberately no OrderingFilter alongside this: cursor
    pagination assumes one stable order per view, and letting clients flip it
    per-request would invalidate outstanding cursors."""

    page_size = 20
    ordering = "-created_at"
