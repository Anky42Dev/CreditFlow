from rest_framework.exceptions import ValidationError

from common.exceptions import ConflictError

from .models import Profile, User

MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png"}


def register_user(email: str, password: str) -> User:
    """DOC 0 §6.2. Profile is created automatically by the post_save signal
    (see apps/accounts/signals.py) — no manual Profile.objects.create here.
    """
    if User.objects.filter(email=email).exists():
        raise ConflictError(code="EMAIL_TAKEN", message="Email already registered")
    user = User.objects.create_user(email=email, password=password)
    return user


def validate_avatar(file) -> None:
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise ValidationError({"avatar": ["Only JPEG/PNG allowed"]})
    if file.size > MAX_AVATAR_SIZE:
        raise ValidationError({"avatar": ["File too large (max 2MB)"]})


def upload_avatar(profile: Profile, file) -> None:
    """DOC 5 §9, Roadmap Этап 5 п.13: validates synchronously (cheap, needs
    to surface 400s to the client immediately) then defers the actual
    resize+save to a Celery task (apps.accounts.tasks.process_avatar) —
    the client learns the final avatar URL via WS push (event
    `avatar_updated`, apps.realtime.push.push_avatar_updated), not the
    response body.
    """
    from .tasks import process_avatar

    validate_avatar(file)
    process_avatar.delay(profile.id, file.read())
