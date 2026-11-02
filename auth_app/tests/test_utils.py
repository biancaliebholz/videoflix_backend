"""Tests for the stateless helpers in ``auth_app.utils``."""

from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings

from auth_app.tests.helpers import create_user
from auth_app.utils import (
    account_activation_token,
    build_frontend_link,
    encode_uid,
    get_user_by_uid,
)


class UidTests(TestCase):

    def test_encoded_uid_resolves_to_user(self):
        user = create_user()
        self.assertEqual(get_user_by_uid(encode_uid(user)), user)

    def test_invalid_or_unknown_uid_returns_none(self):
        for uidb64 in ("not-base64!", "", "OTk5OTk"):
            with self.subTest(uidb64=uidb64):
                self.assertIsNone(get_user_by_uid(uidb64))


class FrontendLinkTests(TestCase):

    @override_settings(FRONTEND_URL="http://frontend.test")
    def test_link_points_to_frontend_page_with_query(self):
        link = build_frontend_link("activate.html", "MQ", "abc-123")
        self.assertEqual(
            link,
            "http://frontend.test/pages/auth/activate.html"
            "?uid=MQ&token=abc-123",
        )


class ActivationTokenTests(TestCase):

    def test_token_is_invalid_once_account_is_active(self):
        user = create_user(is_active=False)
        token = account_activation_token.make_token(user)
        self.assertTrue(account_activation_token.check_token(user, token))
        user.is_active = True
        self.assertFalse(account_activation_token.check_token(user, token))

    def test_activation_token_cannot_reset_password(self):
        """Separate salts keep both token types apart."""
        user = create_user(is_active=False)
        token = account_activation_token.make_token(user)
        self.assertFalse(default_token_generator.check_token(user, token))
