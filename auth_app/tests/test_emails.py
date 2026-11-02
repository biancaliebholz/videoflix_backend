"""Tests for email rendering, the RQ email tasks and their queueing."""

import re
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from auth_app.services import email_service
from auth_app.tasks import queue_activation_email, send_activation_email_task
from auth_app.tests.helpers import create_user
from auth_app.utils import account_activation_token, get_user_by_uid

LINK_PATTERN = r"{page}\?uid=(?P<uid>[\w-]+)&token=(?P<token>[\w-]+)"


def extract_link_params(body, page):
    return re.search(LINK_PATTERN.format(page=re.escape(page)), body)


@override_settings(FRONTEND_URL="http://frontend.test")
class ActivationEmailTests(TestCase):

    def setUp(self):
        self.user = create_user("new@example.com", is_active=False)
        email_service.send_activation_email(self.user)
        self.message = mail.outbox[0]

    def test_email_is_sent_to_user_with_design_subject(self):
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.message.to, ["new@example.com"])
        self.assertEqual(self.message.subject, "Confirm your email")

    def test_link_targets_frontend_activation_page(self):
        self.assertIn(
            "http://frontend.test/pages/auth/activate.html?uid=",
            self.message.body,
        )

    def test_link_contains_valid_activation_token(self):
        params = extract_link_params(self.message.body, "activate.html")
        self.assertEqual(get_user_by_uid(params["uid"]), self.user)
        self.assertTrue(
            account_activation_token.check_token(self.user, params["token"])
        )

    def test_html_version_contains_button_link_and_inline_logo(self):
        html, mimetype = self.message.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn("Activate account", html)
        self.assertIn("cid:videoflix-logo", html)
        logo = self.message.attachments[0]
        self.assertEqual(logo["Content-ID"], "<videoflix-logo>")


class ActivationTaskTests(TestCase):

    def test_task_sends_email_for_existing_user(self):
        user = create_user(is_active=False)
        send_activation_email_task(user.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_task_ignores_deleted_user(self):
        send_activation_email_task(999999)
        self.assertEqual(len(mail.outbox), 0)

    @patch("auth_app.tasks.django_rq.enqueue")
    def test_queueing_puts_email_job_in_front_of_long_jobs(self, enqueue):
        queue_activation_email(42)
        args, kwargs = enqueue.call_args
        self.assertEqual(args, (send_activation_email_task, 42))
        self.assertTrue(kwargs["at_front"])
