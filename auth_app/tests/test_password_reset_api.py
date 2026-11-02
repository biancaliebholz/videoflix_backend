"""Tests for the password reset request and confirmation flow."""

from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.services import email_service
from auth_app.tasks import (
    queue_password_reset_email,
    send_password_reset_email_task,
)
from auth_app.tests.helpers import PASSWORD, create_user
from auth_app.tests.test_emails import extract_link_params
from auth_app.utils import (
    account_activation_token,
    encode_uid,
    get_user_by_uid,
)

QUEUE_PATH = (
    "auth_app.services.password_reset_service.queue_password_reset_email"
)
RESET_SENT = "An email has been sent to reset your password."
NEW_PASSWORD = "Neues!Passwort2027"


@patch(QUEUE_PATH)
class PasswordResetRequestApiTests(APITestCase):

    url = reverse("password_reset")

    def request_reset(self, email):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, {"email": email}, format="json")

    def test_active_user_gets_reset_email_queued(self, queue):
        user = create_user("max@example.com")
        response = self.request_reset("MAX@example.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"detail": RESET_SENT})
        queue.assert_called_once_with(user.pk)

    def test_unknown_or_inactive_email_gets_same_response(self, queue):
        create_user("inactive@example.com", is_active=False)
        for email in ("unknown@example.com", "inactive@example.com"):
            with self.subTest(email=email):
                response = self.request_reset(email)
                self.assertEqual(response.data, {"detail": RESET_SENT})
        queue.assert_not_called()

    def test_invalid_email_format_is_rejected(self, queue):
        self.assertEqual(self.request_reset("no-email").status_code, 400)


class PasswordConfirmApiTests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.uidb64 = encode_uid(self.user)
        self.token = default_token_generator.make_token(self.user)

    def confirm(self, new=NEW_PASSWORD, repeat=NEW_PASSWORD, token=None):
        url = reverse(
            "password_confirm", args=[self.uidb64, token or self.token]
        )
        data = {"new_password": new, "confirm_password": repeat}
        return self.client.post(url, data, format="json")

    def test_valid_link_sets_new_password(self):
        response = self.confirm()
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"detail": "Your Password has been successfully reset."},
        )
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_link_cannot_be_used_twice(self):
        self.confirm()
        self.assertEqual(self.confirm().status_code, 400)

    def test_invalid_or_activation_token_is_rejected(self):
        activation = account_activation_token.make_token(self.user)
        for token in ("wrong-token", activation):
            with self.subTest(token=token[:8]):
                self.assertEqual(self.confirm(token=token).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_expired_link_is_rejected(self):
        self.assertEqual(self.confirm().status_code, 400)

    def test_mismatching_passwords_are_rejected(self):
        response = self.confirm(repeat="Anderes!Passwort1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_password", response.data)

    def test_weak_password_is_rejected(self):
        response = self.confirm(new="12345678", repeat="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_password", response.data)

    def test_existing_sessions_are_logged_out(self):
        refresh = RefreshToken.for_user(self.user)
        self.confirm()
        jti = refresh["jti"]
        blacklisted = BlacklistedToken.objects.filter(token__jti=jti)
        self.assertTrue(blacklisted.exists())


@override_settings(FRONTEND_URL="http://frontend.test")
class PasswordResetEmailTests(TestCase):

    def test_email_links_to_frontend_confirm_page(self):
        user = create_user()
        email_service.send_password_reset_email(user)
        message = mail.outbox[0]
        params = extract_link_params(message.body, "confirm_password.html")
        self.assertEqual(message.subject, "Reset your Password")
        self.assertIn("http://frontend.test/pages/auth/", message.body)
        self.assertEqual(get_user_by_uid(params["uid"]), user)
        self.assertTrue(
            default_token_generator.check_token(user, params["token"])
        )

    def test_email_mentions_24_hour_validity(self):
        email_service.send_password_reset_email(create_user())
        html, _ = mail.outbox[0].alternatives[0]
        self.assertIn("24 hours", html)
        self.assertIn("Reset password", html)

    def test_task_sends_email_to_active_user(self):
        send_password_reset_email_task(create_user().pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_task_skips_inactive_users(self):
        user = create_user(is_active=False)
        send_password_reset_email_task(user.pk)
        self.assertEqual(len(mail.outbox), 0)

    @patch("auth_app.tasks.django_rq.enqueue")
    def test_queueing_uses_front_of_queue(self, enqueue):
        queue_password_reset_email(7)
        args, kwargs = enqueue.call_args
        self.assertEqual(args, (send_password_reset_email_task, 7))
        self.assertTrue(kwargs["at_front"])
