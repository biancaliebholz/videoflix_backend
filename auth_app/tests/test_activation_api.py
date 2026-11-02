"""Tests for ``GET /api/activate/<uidb64>/<token>/``."""

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from auth_app.tests.helpers import create_user
from auth_app.utils import account_activation_token, encode_uid


class ActivationApiTests(APITestCase):

    def setUp(self):
        self.user = create_user(is_active=False)
        self.uidb64 = encode_uid(self.user)
        self.token = account_activation_token.make_token(self.user)

    def activate(self, uidb64=None, token=None):
        url = reverse(
            "activate", args=[uidb64 or self.uidb64, token or self.token]
        )
        return self.client.get(url)

    def test_valid_link_activates_account(self):
        response = self.activate()
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"message": "Account successfully activated."}
        )
        self.assertTrue(self.user.is_active)

    def test_invalid_token_or_uid_is_rejected(self):
        for uidb64, token in (
            (None, "wrong-token"), ("invalid", None), ("OTk5OTk", None)
        ):
            with self.subTest(uidb64=uidb64, token=token):
                response = self.activate(uidb64, token)
                self.assertEqual(response.status_code, 400)
                self.assertIn("message", response.data)

    def test_link_cannot_be_used_twice(self):
        self.activate()
        self.assertEqual(self.activate().status_code, 400)

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_expired_link_is_rejected(self):
        self.assertEqual(self.activate().status_code, 400)

    def test_stale_access_cookie_does_not_block_activation(self):
        self.client.cookies["access_token"] = "expired-or-garbage"
        self.assertEqual(self.activate().status_code, 200)
