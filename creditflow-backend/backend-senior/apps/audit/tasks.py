import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_future_partitions(self):
    """DOC 5 §14, Roadmap Этап 5 п.14: monthly Celery Beat entry point (see
    config/settings.py CELERY_BEAT_SCHEDULE) for
    apps.audit.services.create_future_partitions — keeps audit_logs/
    transactions provisioned with upcoming monthly partitions ahead of time."""
    from .services import create_future_partitions as _create_future_partitions

    try:
        _create_future_partitions(months_ahead=3)
    except Exception as exc:
        logger.exception(
            "create_future_partitions failed (attempt %s/%s)",
            self.request.retries + 1, self.max_retries,
        )
        raise self.retry(exc=exc)
