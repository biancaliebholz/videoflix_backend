"""Tests for ``POST /api/login/`` and the issued auth cookies."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from auth_app.tests.helpers import FRONTEND_ORIGIN, PASSWORD, create_user

GENERIC_ERROR = "Please check your input and try again."


class LoginApiTests(APITestCase):

    url = reverse("login")

    def setUp(self):
        self.user = create_user("max@example.com")

    def login(self, email="max@example.com", password=PASSWORD):
        data = {"email": email, "password": password}
        return self.client.post(self.url, data, format="json")

    def test_valid_credentials_return_user_without_tokens(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            "detail": "Login successful",
            "user": {"id": self.user.id, "username": "max@example.com"},
        })

    def test_auth_cookies_are_httponly_lax_and_host_only(self):
        cookies = self.login().cookies
        expected = (("access_token", 1800), ("refresh_token", 86400))
        for name, max_age in expected:
            with self.subTest(cookie=name):
                cookie = cookies[name]
                self.assertTrue(cookie["httponly"])
                self.assertEqual(cookie["samesite"], "Lax")
                self.assertEqual(cookie["path"], "/")
                self.assertEqual(cookie["domain"], "")
                self.assertEqual(cookie["max-age"], max_age)

    def test_email_letter_case_is_ignored(self):
        self.assertEqual(self.login(email="MAX@Example.com").status_code, 200)

    def test_last_login_is_updated(self):
        self.login()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_failures_share_one_generic_message(self):
        create_user("inactive@example.com", is_active=False)
        for email, password in (
            ("max@example.com", "falsch"),
            ("unknown@example.com", PASSWORD),
            ("inactive@example.com", PASSWORD),
        ):
            with self.subTest(email=email):
                response = self.login(email, password)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["detail"], [GENERIC_ERROR])
                self.assertNotIn("access_token", response.cookies)

    def test_stale_access_cookie_does_not_block_login(self):
        self.client.cookies["access_token"] = "garbage"
        response = self.client.post(
            self.url,
            {"email": "max@example.com", "password": PASSWORD},
            format="json",
            HTTP_ORIGIN=FRONTEND_ORIGIN,
        )
        self.assertEqual(response.status_code, 200)
