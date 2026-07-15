import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def score_application(self, application_id):
    """Roadmap Этап 3 п.7-8: goes through ApplyScoringDecisionUseCase (which
    still calls the unchanged apps.applications.services.perform_scoring
    internally) instead of calling perform_scoring directly, so the
    ApplicationApproved/ApplicationRejected domain event this task's scoring
    decision raises reaches the transactional outbox — see that use case's
    docstring."""
    from lending.infrastructure.di import container

    try:
        with transaction.atomic():
            container.apply_scoring_decision().execute(application_id)
    except Exception as exc:
        logger.exception(
            "score_application failed for application_id=%s (attempt %s/%s)",
            application_id, self.request.retries + 1, self.max_retries,
        )
        raise self.retry(exc=exc)
