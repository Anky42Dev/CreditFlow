import io
import logging

from celery import shared_task
from django.core.files.base import ContentFile
from PIL import Image

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_avatar(self, profile_id: int, raw_bytes: bytes):
    """DOC 5 §9, Roadmap Этап 5 п.13: resize + save the avatar off the
    request/response cycle, result in S3 (or local storage in dev — see
    config/settings.py USE_S3). Validation (content-type/size) already ran
    synchronously in the view (apps.accounts.services.validate_avatar) before
    this task was queued, so failures here are unexpected and get retried
    rather than surfaced to the user.
    """
    from apps.realtime.push import push_avatar_updated

    from .models import Profile

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image = image.convert("RGB")
        image.thumbnail((400, 400))

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)

        profile = Profile.objects.get(pk=profile_id)
        profile.avatar.save(f"{profile.id}.jpg", ContentFile(buffer.read()), save=True)
        push_avatar_updated(profile.user_id, profile.avatar.url)
    except Exception as exc:
        logger.exception(
            "process_avatar failed for profile_id=%s (attempt %s/%s)",
            profile_id, self.request.retries + 1, self.max_retries,
        )
        raise self.retry(exc=exc)
