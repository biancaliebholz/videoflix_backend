"""Tests for the origin based CSRF protection and the CORS configuration."""

from types import SimpleNamespace
from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APIRequestFactory, APITestCase

from auth_app.api.permissions import IsTrustedOrigin
from auth_app.tests.helpers import FRONTEND_ORIGIN, PASSWORD, create_user

EVIL_ORIGIN = "http://evil.example"


def permission_for(method="post", origin=None, cookies=None):
    headers = {"HTTP_ORIGIN": origin} if origin else {}
    request = getattr(APIRequestFactory(), method)("/", **headers)
    request.COOKIES.update(cookies or {})
    wrapped = SimpleNamespace(
        method=request.method, headers=request.headers, COOKIES=request.COOKIES
    )
    return IsTrustedOrigin().has_permission(wrapped, view=None)


class IsTrustedOriginTests(APITestCase):

    def test_safe_methods_are_always_allowed(self):
        self.assertTrue(permission_for("get", origin=EVIL_ORIGIN))

    def test_trusted_origin_is_allowed(self):
        self.assertTrue(permission_for(origin=FRONTEND_ORIGIN))

    def test_foreign_or_null_origin_is_rejected(self):
        for origin in (EVIL_ORIGIN, "null"):
            with self.subTest(origin=origin):
                self.assertFalse(permission_for(origin=origin))

    def test_missing_origin_is_allowed_without_auth_cookies(self):
        self.assertTrue(permission_for())

    def test_missing_origin_is_rejected_with_auth_cookies(self):
        self.assertFalse(permission_for(cookies={"refresh_token": "x"}))


@patch("auth_app.services.registration_service.queue_activation_email")
class CrossSiteRequestTests(APITestCase):

    def setUp(self):
        create_user("max@example.com")
        self.client.cookies["refresh_token"] = "victim-token"

    def test_unsafe_endpoints_reject_foreign_origin(self, queue):
        payload = {"email": "max@example.com", "password": PASSWORD}
        for name in ("register", "login", "logout", "token_refresh"):
            with self.subTest(endpoint=name):
                response = self.client.post(
                    reverse(name), payload, format="json",
                    HTTP_ORIGIN=EVIL_ORIGIN,
                )
                self.assertEqual(response.status_code, 403)

    def test_frontend_origin_can_log_in(self, queue):
        response = self.client.post(
            reverse("login"),
            {"email": "max@example.com", "password": PASSWORD},
            format="json",
            HTTP_ORIGIN=FRONTEND_ORIGIN,
        )
        self.assertEqual(response.status_code, 200)


class CorsTests(APITestCase):

    def preflight(self, origin):
        return self.client.options(
            reverse("login"),
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

    def test_frontend_origin_may_send_credentials(self):
        response = self.preflight(FRONTEND_ORIGIN)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], FRONTEND_ORIGIN
        )
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")

    def test_foreign_origin_gets_no_cors_headers(self):
        response = self.preflight(EVIL_ORIGIN)
        self.assertNotIn("Access-Control-Allow-Origin", response)
