"""Custom user model that logs in with a unique email address."""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

EMAIL_MAX_LENGTH = 254


class UserManager(BaseUserManager):
    """Create users and superusers identified by their email address."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        """Return the email trimmed and completely lower-cased."""
        return super().normalize_email(email).strip().lower()

    def get_by_natural_key(self, email):
        """Look up a user by email, ignoring letter case and whitespace."""
        field = self.model.USERNAME_FIELD
        return self.get(**{field: self.normalize_email(email)})

    def create_user(self, email, password=None, **extra_fields):
        """Create an inactive regular user that still needs activation."""
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        """Create an active superuser, also when called with ``username``."""
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        self._validate_superuser_flags(extra_fields)
        return self._create_user(email, password, **extra_fields)

    def _create_user(self, email, password, **extra_fields):
        """Save a user with normalized email and hashed password."""
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    @staticmethod
    def _validate_superuser_flags(extra_fields):
        """Reject superusers without staff or superuser rights."""
        for flag in ("is_staff", "is_superuser"):
            if extra_fields.get(flag) is not True:
                raise ValueError(f"Superuser must have {flag}=True.")


class User(AbstractUser):
    """Videoflix user; ``username`` is kept for the Docker entrypoint."""

    username = models.CharField(
        _("username"),
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
        help_text=_("Defaults to the email address."),
    )
    email = models.EmailField(
        _("email address"), max_length=EMAIL_MAX_LENGTH, unique=True
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        """Return the email address as readable representation."""
        return self.email
