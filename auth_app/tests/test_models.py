"""Tests for the custom email-based user model and its manager."""

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase

from auth_app.models import User

PASSWORD = "Sicher!Passwort2026"
MAX_LENGTH_EMAIL = "a" * 64 + "@" + "b" * 63 + "." + "c" * 63 + "." + "d" * 61


class CreateUserTests(TestCase):
    """Behaviour of ``UserManager.create_user``."""

    def test_email_is_login_field(self):
        """The email address is used as the login identifier."""
        user = User.objects.create_user("max@example.com", PASSWORD)
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(user.get_username(), "max@example.com")

    def test_email_is_trimmed_and_lowercased(self):
        """Emails are stored in a single canonical form."""
        user = User.objects.create_user("  Max.Muster@Example.COM ", PASSWORD)
        self.assertEqual(user.email, "max.muster@example.com")

    def test_username_defaults_to_email(self):
        """A username is filled automatically for the entrypoint script."""
        user = User.objects.create_user("max@example.com", PASSWORD)
        self.assertEqual(user.username, "max@example.com")

    def test_new_user_is_inactive_and_unprivileged(self):
        """New accounts need email activation and get no admin rights."""
        user = User.objects.create_user("max@example.com", PASSWORD)
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_is_hashed(self):
        """The raw password is never stored."""
        user = User.objects.create_user("max@example.com", PASSWORD)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_missing_email_raises_error(self):
        """An email address is mandatory."""
        with self.assertRaises(ValueError):
            User.objects.create_user("", PASSWORD)

    def test_email_is_unique_case_insensitively(self):
        """Case variants of an existing email are rejected."""
        User.objects.create_user("max@example.com", PASSWORD)
        with self.assertRaises(IntegrityError):
            User.objects.create_user("MAX@example.com", PASSWORD)


class CreateSuperuserTests(TestCase):
    """Behaviour of ``UserManager.create_superuser``."""

    def test_entrypoint_signature_is_supported(self):
        """The unchanged Docker entrypoint call works as before."""
        User.objects.create_superuser(
            username="admin", email="admin@example.com", password=PASSWORD
        )
        admin = User.objects.get(username="admin")
        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_superuser_flags_cannot_be_disabled(self):
        """A superuser without staff or superuser rights is rejected."""
        for flag in ("is_staff", "is_superuser"):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                User.objects.create_superuser(
                    "admin@example.com", PASSWORD, **{flag: False}
                )


class UserModelTests(TestCase):
    """Field definitions and model level behaviour."""

    def test_auth_user_model_points_to_custom_user(self):
        """Django uses the custom model everywhere."""
        self.assertIs(get_user_model(), User)

    def test_username_fits_longest_valid_email(self):
        """Username and email share the RFC maximum of 254 characters."""
        user = User.objects.create_user(MAX_LENGTH_EMAIL, PASSWORD)
        self.assertEqual(len(user.username), 254)
        self.assertEqual(User._meta.get_field("username").max_length, 254)
        self.assertEqual(User._meta.get_field("email").max_length, 254)

    def test_clean_normalizes_email(self):
        """Admin forms run ``clean()`` and get the same normalization."""
        user = User(email=" New@Example.DE ", username="new")
        user.clean()
        self.assertEqual(user.email, "new@example.de")

    def test_str_returns_email(self):
        """The string representation is the email address."""
        user = User.objects.create_user("max@example.com", PASSWORD)
        self.assertEqual(str(user), "max@example.com")


class AuthenticationTests(TestCase):
    """Login behaviour of Django's default ``ModelBackend``."""

    def test_active_user_authenticates_case_insensitively(self):
        """Login works regardless of email letter case."""
        user = User.objects.create_user(
            "max@example.com", PASSWORD, is_active=True
        )
        result = authenticate(email="MAX@Example.com", password=PASSWORD)
        self.assertEqual(result, user)

    def test_inactive_user_cannot_authenticate(self):
        """Accounts without activation cannot log in."""
        User.objects.create_user("max@example.com", PASSWORD)
        self.assertIsNone(
            authenticate(email="max@example.com", password=PASSWORD)
        )


class MigrationStateTests(TestCase):
    """The committed migrations match the current models."""

    def test_no_missing_migrations(self):
        """The entrypoint's ``makemigrations`` must find nothing to do."""
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)
