"""DOC 5 §12.3: OpenTelemetry tracing. Auto-instruments Django, psycopg2 and
redis. Exports to Jaeger via OTLP/HTTP when OTEL_EXPORTER_OTLP_ENDPOINT is
set (docker-compose.prod, Roadmap Этап 8 — AC-9); falls back to
ConsoleSpanExporter otherwise (dev/CI, no collector running).

Manual spans cover the parts auto-instrumentation can't see — the Outbox
Relay/consumer loop and the loan-issuance saga run outside any HTTP
request/response cycle — via `get_tracer(__name__)` from the call site (see
apps.outbox.tasks, apps.outbox.consumers,
src.lending.application.sagas.loan_issuance_saga).
"""

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

_configured = False


def configure_tracing() -> None:
    """Idempotent: config/settings.py can be imported more than once per
    process (autoreload, management commands, tests), and OTel's
    instrumentors/set_tracer_provider warn loudly if run twice.
    """
    global _configured
    if _configured:
        return
    _configured = True

    provider = TracerProvider(
        resource=Resource.create({"service.name": "creditflow-backend-senior"})
    )
    # Spans still get created/started under pytest (instrumentation stays
    # active so the code paths are exercised), just not exported — pytest
    # sets PYTEST_VERSION for the whole session, so this doesn't need a
    # pytest.ini/conftest.py hook of its own.
    if not os.environ.get("PYTEST_VERSION"):
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            # BatchSpanProcessor exports off a background worker thread, so
            # a slow/unreachable Jaeger doesn't block the request thread —
            # SimpleSpanProcessor exports synchronously inline and, verified
            # while bringing up docker-compose.prod, stalls every DB-touching
            # request for seconds (per-span retry+backoff) whenever Jaeger
            # isn't reachable yet.
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces"))
            )
        else:
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    DjangoInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()


def get_tracer(name: str):
    return trace.get_tracer(name)
