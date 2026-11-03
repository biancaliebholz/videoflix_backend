"""Django RQ jobs for sending authentication emails in the background.

Email jobs are queued at the front of the single ``default`` queue so they
are not delayed behind long running video conversions.
"""

import django_rq
from rq import Retry

from auth_app.models import User
from auth_app.services import email_service

EMAIL_RETRY = Retry(max=3)


def send_activation_email_task(user_id):
    """Send the activation email; skip users deleted in the meantime."""
    user = User.objects.filter(pk=user_id).first()
    if user is not None:
        email_service.send_activation_email(user)


def send_password_reset_email_task(user_id):
    """Send the reset email only if the account is still active."""
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is not None:
        email_service.send_password_reset_email(user)


def queue_activation_email(user_id):
    _queue_email(send_activation_email_task, user_id)


def queue_password_reset_email(user_id):
    _queue_email(send_password_reset_email_task, user_id)


def _queue_email(task, user_id):
    """Queue ahead of conversions, retried up to three times on errors."""
    django_rq.enqueue(task, user_id, at_front=True, retry=EMAIL_RETRY)
