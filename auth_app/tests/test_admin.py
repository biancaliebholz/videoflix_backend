"""Tests for the Django admin integration of the custom user model."""

from django.test import TestCase
from django.urls import reverse

from auth_app.models import User

PASSWORD = "Sicher!Passwort2026"


class UserAdminTests(TestCase):
    """The admin pages work with email-based users."""

    def setUp(self):
        """Log in as a superuser."""
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password=PASSWORD
        )
        self.client.force_login(self.admin)

    def test_changelist_page_loads(self):
        """The user list renders."""
        response = self.client.get(reverse("admin:auth_app_user_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_change_page_loads(self):
        """The edit page of a user renders."""
        url = reverse("admin:auth_app_user_change", args=[self.admin.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_add_page_creates_user_with_normalized_email(self):
        response = self.client.post(
            reverse("admin:auth_app_user_add"),
            {
                "email": "New.User@Example.com",
                "username": "newuser",
                "usable_password": "true",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.filter(email="new.user@example.com")
        self.assertTrue(created.exists())
