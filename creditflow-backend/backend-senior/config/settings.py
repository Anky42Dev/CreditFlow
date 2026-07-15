"""
Django settings for config project (CreditFlow — Backend Senior).
"""

import sys
from datetime import timedelta
from pathlib import Path

import structlog
from celery.schedules import crontab
from decouple import Csv, config

from common.logging import configure_structlog, mask_pii

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# DOC 5 §3: the clean-architecture layer (shared/, lending/, ...) lives under
# src/ as plain packages ("shared.domain...", "lending.domain...") rather than
# nested under apps.*, so it stays importable from a future standalone
# scoring_service too (DOC 5 §7). Needs src/ on sys.path since it's not an
# installed package.
sys.path.insert(0, str(BASE_DIR / "src"))


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "apps.accounts",
    "apps.rbac",
    "apps.products",
    "apps.applications",
    "apps.lending",
    "apps.realtime",
    "apps.notifications",
    "apps.adminpanel",
    "apps.audit",
    "apps.outbox",
    "apps.health",
    "apps.feature_flags",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # DOC 5 §12.2/§12.3: binds request_id/trace_id before anything else logs;
    # DOC 5 §12.1: records cf_http_request_duration_seconds around the full
    # downstream stack (auth, view, exceptions).
    "common.middleware.RequestContextMiddleware",
    "common.middleware.PrometheusMetricsMiddleware",
    # DOC 5 §10.4: runs late on the response path (MIDDLEWARE is reversed
    # for responses) so it stamps headers on every response, including
    # error responses raised deeper in the stack.
    "common.middleware.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# httpOnly refresh cookie + CSRF (DOC 6 §3 — Frontend Senior token security)
REFRESH_COOKIE_NAME = "cf_refresh_token"
REFRESH_COOKIE_SECURE = config("REFRESH_COOKIE_SECURE", default=not DEBUG, cast=bool)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = REFRESH_COOKIE_SECURE
CSRF_COOKIE_HTTPONLY = False  # must be JS-readable for double-submit header

# Security headers (DOC 5 §10.4). HSTS/nosniff go through Django's own
# SecurityMiddleware; CSP has no built-in Django setting, so it's applied by
# common.middleware.SecurityHeadersMiddleware instead, reading CSP_POLICY.
# Off in DEBUG so plain-HTTP local dev isn't redirected/broken.
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
# Roadmap Этап 8 п.20: nginx (deploy/nginx/nginx.conf) terminates TLS and
# forwards plain HTTP to `web` with X-Forwarded-Proto set — without this,
# SECURE_SSL_REDIRECT=True would see every request as insecure and loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"
CSP_POLICY = config(
    "CSP_POLICY",
    default="default-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="creditflow_senior"),
        "USER": config("DB_USER", default="creditflow"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    },
    # DOC 5 §14, Roadmap Этап 5 п.14: read replica for heavy reports/admin
    # analytics (config/db_router.py::ReplicaRouter routes AuditLog reads
    # here). Falls back to the primary's own connection details when
    # REPLICA_DB_* isn't set — a safe no-op locally/in CI, not a real
    # replica. TEST/MIRROR makes pytest run this against the real test
    # Postgres database (same physical DB as 'default' in tests) rather than
    # needing — or creating — a second one.
    "replica": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("REPLICA_DB_NAME", default=config("DB_NAME", default="creditflow_senior")),
        "USER": config("REPLICA_DB_USER", default=config("DB_USER", default="creditflow")),
        "PASSWORD": config("REPLICA_DB_PASSWORD", default=config("DB_PASSWORD", default="")),
        "HOST": config("REPLICA_DB_HOST", default=config("DB_HOST", default="localhost")),
        "PORT": config("REPLICA_DB_PORT", default=config("DB_PORT", default="5432")),
        "TEST": {"MIRROR": "default"},
    },
}

DATABASE_ROUTERS = ["config.db_router.ReplicaRouter"]


# Custom user model (DOC 0 §1.4; DOC 3 §3.1)
AUTH_USER_MODEL = "accounts.User"


# Redis cache — RBAC permission cache (DOC 3 §5.1, §8)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}


# Channels — WebSocket layer (DOC 3 §2, §7; consumers wired in Этап 5)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("CHANNEL_LAYERS_REDIS_URL", default="redis://localhost:6379/2")],
        },
    }
}


# Celery — task queue (DOC 3 §2, §6; tasks added from Этап 3 onward)
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# DOC 5 §15.1, Roadmap Этап 8 п.20: routes tasks onto dedicated queues so
# docker-compose.prod can run one worker container per queue (independent
# scaling for scoring/email/schedule/outbox, per §15.1's "воркеры, отдельно
# скоринг/email/schedule очереди"). Anything not listed here — e.g.
# apps.accounts.tasks.process_avatar — falls through to the default "celery"
# queue, consumed by celery-worker-default in docker-compose.prod.
CELERY_TASK_ROUTES = {
    "apps.applications.tasks.score_application": {"queue": "scoring"},
    "apps.notifications.tasks.send_email_async": {"queue": "email"},
    "apps.notifications.tasks.send_due_reminders": {"queue": "email"},
    "apps.lending.tasks.mark_overdue_payments": {"queue": "schedule"},
    "apps.audit.tasks.create_future_partitions": {"queue": "schedule"},
    "apps.outbox.tasks.relay_outbox_messages": {"queue": "outbox"},
}

# Celery Beat — periodic tasks (DOC 3 §12, Этап 6; outbox relay Этап 3 §18 п.7)
CELERY_BEAT_SCHEDULE = {
    "check-overdue-payments": {
        "task": "apps.lending.tasks.mark_overdue_payments",
        "schedule": crontab(hour=1, minute=0),
    },
    "payment-due-reminders": {
        "task": "apps.notifications.tasks.send_due_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    "relay-outbox": {
        "task": "apps.outbox.tasks.relay_outbox_messages",
        "schedule": 5.0,
    },
    "create-future-partitions": {
        # DOC 5 §14, Roadmap Этап 5 п.14: keeps audit_logs/transactions
        # provisioned with upcoming monthly partitions ahead of time.
        "task": "apps.audit.tasks.create_future_partitions",
        "schedule": crontab(day_of_month=1, hour=0, minute=30),
    },
}

# Broker for domain events (DOC 5 §8, Roadmap Этап 3 п.7-8): transactional
# outbox rows are published here, and apps.outbox.management.commands.
# consume_events consumes from it. Kept separate from CELERY_BROKER_URL
# (Redis, above) — DOC 5 §8.3 assigns RabbitMQ to Saga/domain-event traffic
# specifically. Defaults to kombu's in-memory transport so `runserver`/tests
# work without a running broker; docker-compose overrides it to a real
# RabbitMQ instance for the `celery`/`saga-worker` services.
EVENT_BROKER_URL = config("EVENT_BROKER_URL", default="memory://")

# Email (DOC 3 §11). Console backend for dev; swap via env in production.
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@creditflow.local")


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static / media files

STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# S3/MinIO object storage (DOC 5 §9, Roadmap Этап 5 п.13). Off by default so
# `runserver`/pytest keep using local FileSystemStorage (no MinIO/Docker
# required — see RUNNING.md). Set USE_S3=True + the AWS_S3_* vars below to
# switch avatars/documents to S3Boto3Storage (MinIO locally via a custom
# AWS_S3_ENDPOINT_URL, AWS S3 in prod without it).
USE_S3 = config("USE_S3", default=False, cast=bool)

if USE_S3:
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="creditflow-documents")
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)  # e.g. http://localhost:9000 for MinIO
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_DEFAULT_ACL = None  # private: no public-read ACL on uploaded objects
    # Приватные документы/аватары → presigned URL с TTL (DOC 5 §9), не публичный доступ.
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = config("AWS_QUERYSTRING_EXPIRE", default=3600, cast=int)
    AWS_S3_ADDRESSING_STYLE = "path"  # required by MinIO's default (non-DNS-style) buckets

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


# Django REST Framework (DOC 0 §5)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # DOC 5 §10.3: brute-force protection on auth endpoints + general abuse
    # limits. Backed by CACHES["default"] (Redis), so 429s are shared across
    # workers. "login"/"register" scopes are opt-in per view via
    # throttle_scope; "anon"/"user" apply everywhere else.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
        "register": "10/hour",
        "user": "1000/hour",
        "anon": "100/hour",
    },
}

# drf-spectacular / OpenAPI
SPECTACULAR_SETTINGS = {
    "TITLE": "CreditFlow API — Middle",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# SimpleJWT (DOC 0 §6.1; rotation+blacklist DOC 5 §10.2). Rotation is
# handled entirely inside TokenRefreshSerializer — see
# apps.accounts.views.RefreshView for how the rotated refresh reaches the
# httpOnly cookie, and LogoutView for explicit blacklisting on logout.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Structured JSON logging (DOC 5 §12.2). configure_structlog() sets up the
# processor chain structlog itself uses; the LOGGING dict below routes
# stdlib logging (Django, Celery, third-party) through the same
# ProcessorFormatter so both end up as identical JSON lines on stdout, with
# request_id/trace_id/user_id merged in from contextvars
# (common.middleware.RequestContextMiddleware) and PII redacted (mask_pii).
configure_structlog()

LOG_LEVEL = config("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                mask_pii,
            ],
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

# OpenTelemetry tracing (DOC 5 §12.3). Auto-instruments Django/psycopg2/redis
# and exports spans to the console; kept as a separate module (rather than
# inline here) so tests can import common.tracing without re-triggering
# instrumentation on every settings reload.
from common.tracing import configure_tracing  # noqa: E402

configure_tracing()

# Feature flags (DOC 5 §11) — Redis-backed, kept on its own DB index rather
# than CACHES["default"]'s (db 1) so a cache-wide FLUSHDB in ops doesn't also
# nuke flag state.
FEATURE_FLAGS_REDIS_URL = config(
    "FEATURE_FLAGS_REDIS_URL", default="redis://localhost:6379/3"
)
