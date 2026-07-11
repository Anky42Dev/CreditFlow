import io

from django.core.files.base import ContentFile
from PIL import Image
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


def upload_avatar(profile: Profile, file) -> Profile:
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise ValidationError({"avatar": ["Only JPEG/PNG allowed"]})
    if file.size > MAX_AVATAR_SIZE:
        raise ValidationError({"avatar": ["File too large (max 2MB)"]})

    image = Image.open(file)
    image = image.convert("RGB")
    image.thumbnail((400, 400))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)

    profile.avatar.save(f"{profile.id}.jpg", ContentFile(buffer.read()), save=True)
    return profile
