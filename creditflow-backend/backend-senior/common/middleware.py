import time
import uuid

import structlog
from django.conf import settings

REQUEST_ID_HEADER = "X-Request-Id"
TRACE_ID_HEADER = "X-Trace-Id"


class RequestContextMiddleware:
    """DOC 5 §12.2/§12.3: binds request_id/trace_id (+ user_id, once known)
    into structlog's contextvars so every log line emitted while handling
    this request carries them, and echoes both back as response headers.

    `trace_id` is read from an inbound X-Trace-Id header when present
    (letting a caller/gateway supply one) or generated otherwise. It's picked
    up by shared.infrastructure.outbox.DjangoOutboxStore.append (via these
    same contextvars) and stamped onto the OutboxMessage row written during
    this request, so the Outbox Relay can carry it into the broker payload —
    the same trace_id then threads through scoring_service and back into
    apps.outbox.consumers when ScoringCompleted is applied.

    Placed right after SecurityMiddleware (config/settings.py MIDDLEWARE) so
    it's bound before django.contrib.auth's AuthenticationMiddleware runs —
    that means request.user isn't resolved yet on entry, so user_id can only
    be bound after get_response() returns (best-effort enrichment for logs
    emitted by this middleware itself and for the audit trail, not for
    request-time log lines from deeper in the stack).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        trace_id = request.META.get("HTTP_X_TRACE_ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, trace_id=trace_id)
        try:
            response = self.get_response(request)
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                structlog.contextvars.bind_contextvars(user_id=user.id)
            response[REQUEST_ID_HEADER] = request_id
            response[TRACE_ID_HEADER] = trace_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()


class PrometheusMetricsMiddleware:
    """DOC 5 §12.1: cf_http_request_duration_seconds{endpoint,method,status}.
    `endpoint` uses resolver_match.view_name (a stable route name) rather
    than the raw path, so paths with PK/slug segments don't blow up cardinality.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from common.metrics import http_request_duration_seconds

        start = time.monotonic()
        response = self.get_response(request)
        endpoint = (
            request.resolver_match.view_name if request.resolver_match else "unresolved"
        )
        http_request_duration_seconds.labels(
            endpoint=endpoint, method=request.method, status=response.status_code
        ).observe(time.monotonic() - start)
        return response


class SecurityHeadersMiddleware:
    """DOC 5 §10.4: adds the one security header Django has no built-in
    setting for (CSP). HSTS/nosniff/X-Frame-Options are Django's own
    SecurityMiddleware/XFrameOptionsMiddleware, driven by the SECURE_*
    settings in config/settings.py.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", settings.CSP_POLICY)
        return response
