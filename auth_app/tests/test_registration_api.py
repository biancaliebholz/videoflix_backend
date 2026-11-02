"""Tests for ``POST /api/register/`` and the registration service."""

from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from auth_app.models import User
from auth_app.tests.helpers import PASSWORD, create_user

QUEUE_PATH = "auth_app.services.registration_service.queue_activation_email"
GENERIC_ERROR = "Please check your input and try again."


def registration_data(**overrides):
    data = {
        "email": "new@example.com",
        "password": PASSWORD,
        "confirmed_password": PASSWORD,
    }
    return {**data, **overrides}


@patch(QUEUE_PATH)
class RegistrationApiTests(APITestCase):

    url = reverse("register")

    def register(self, **overrides):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                self.url, registration_data(**overrides), format="json"
            )

    def test_creates_inactive_user_and_returns_201(self, queue):
        response = self.register()
        user = User.objects.get(email="new@example.com")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data, {"user": {"id": user.id, "email": user.email}}
        )
        self.assertFalse(user.is_active)

    def test_response_never_contains_activation_token(self, queue):
        response = self.register()
        self.assertNotIn("token", response.data)
        self.assertNotIn("token", str(response.content))

    def test_activation_email_is_queued_after_commit(self, queue):
        self.register()
        queue.assert_called_once_with(User.objects.get().pk)

    def test_email_is_normalized(self, queue):
        self.register(email="  New@Example.COM ")
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_password_mismatch_is_rejected(self, queue):
        response = self.register(confirmed_password="Anderes!Passwort1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self, queue):
        response = self.register(
            password="12345678", confirmed_password="12345678"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_existing_email_gets_generic_error(self, queue):
        create_user("new@example.com")
        response = self.register(email="NEW@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["email"], [GENERIC_ERROR])
        queue.assert_not_called()

    def test_missing_fields_are_rejected(self, queue):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            set(response.data), {"email", "password", "confirmed_password"}
        )

    def test_accepted_privacy_policy_from_frontend_form(self, queue):
        response = self.register(privacy_policy="on")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_declined_privacy_policy_is_rejected(self, queue):
        response = self.register(privacy_policy=False)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("privacy_policy", response.data)

    def test_form_encoded_requests_are_rejected(self, queue):
        response = self.client.post(self.url, registration_data())
        self.assertEqual(
            response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )
