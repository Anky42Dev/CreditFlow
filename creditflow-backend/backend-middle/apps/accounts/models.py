from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model, email-based auth (DOC 0 §1.4, §6.1-6.2; DOC 3 §3.1).

    `role` is a denormalized pointer to the user's primary role, kept for
    fast checks. Full RBAC (Role/Permission/UserRole tables) is introduced
    on later Middle stages (DOC 3 §3.1, §5) and will reference this field.
    """

    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        SUPPORT = "SUPPORT", "Support"
        UNDERWRITER = "UNDERWRITER", "Underwriter"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return self.email


class Profile(models.Model):
    """Doc 3 §6.3: income/birth_date feed the scoring algorithm."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profiles"

    def __str__(self):
        return f"Profile<{self.user_id}>"
