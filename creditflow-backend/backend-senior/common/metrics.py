"""DOC 5 §12.1: Prometheus counters/histograms + the /metrics exposition
view. Metric objects are module-level (prometheus_client's registry is a
process-global singleton) so every call site imports the same instance
instead of re-registering it.
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from django.http import HttpResponse

applications_submitted_total = Counter(
    "cf_applications_submitted_total",
    "Credit applications submitted.",
)

scoring_duration_seconds = Histogram(
    "cf_scoring_duration_seconds",
    "Time from application submission to a scoring decision being applied.",
)

loans_disbursed_amount_total = Counter(
    "cf_loans_disbursed_amount_total",
    "Total principal amount disbursed across issued loans.",
)

http_request_duration_seconds = Histogram(
    "cf_http_request_duration_seconds",
    "HTTP request duration.",
    ["endpoint", "method", "status"],
)


def metrics_view(request) -> HttpResponse:
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
