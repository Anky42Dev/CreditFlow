import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def score_application(self, application_id):
    from .services import perform_scoring

    try:
        with transaction.atomic():
            perform_scoring(application_id)
    except Exception as exc:
        logger.exception(
            "score_application failed for application_id=%s (attempt %s/%s)",
            application_id, self.request.retries + 1, self.max_retries,
        )
        raise self.retry(exc=exc)
