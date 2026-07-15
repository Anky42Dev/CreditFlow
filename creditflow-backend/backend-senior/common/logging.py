"""DOC 5 §12.2: structured JSON logging. `configure_structlog()` is called
once from config/settings.py; the actual JSON rendering happens in Django's
own LOGGING dict via `structlog.stdlib.ProcessorFormatter` so stdlib loggers
(Django, Celery, third-party libs) and structlog loggers both end up as the
same JSON shape on stdout.

`trace_id`/`request_id`/`user_id` aren't bound here — that's
common.middleware.RequestContextMiddleware, via structlog.contextvars, which
merge_contextvars below picks up on every log call for the life of the
request.
"""

import structlog

# DOC 5 §12.2 "PII маскируется": redact by key name rather than trying to
# parse values, since callers pass PII as keyword args to log calls
# (log.info("...", email=user.email)) — matching key names is exact where
# scanning free-text values would be lossy and slow.
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "access",
        "refresh",
        "authorization",
        "email",
        "phone",
        "ssn",
        "passport",
        "monthly_income",
        "birth_date",
        "card_number",
        "cvv",
    }
)


def mask_pii(logger, method_name, event_dict):
    for key in list(event_dict):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***"
    return event_dict


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            mask_pii,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
