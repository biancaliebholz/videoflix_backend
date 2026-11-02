"""Password reset: requesting a reset link and setting a new password."""

from django.contrib.auth.tokens import default_token_generator
from django.db import transaction

from auth_app.models import User
from auth_app.services.session_service import blacklist_all_refresh_tokens
from auth_app.tasks import queue_password_reset_email
from auth_app.utils import get_user_by_uid


def request_password_reset(email):
    """Queue a reset email for an active account; ignore everything else.

    The caller always answers the same way, so the endpoint does not reveal
    which email addresses are registered.
    """
    email = User.objects.normalize_email(email)
    user = User.objects.filter(email=email, is_active=True).first()
    if user is not None:
        transaction.on_commit(lambda: queue_password_reset_email(user.pk))


def get_user_for_reset(uidb64, token):
    """Return the user of a valid, unexpired reset link or ``None``."""
    user = get_user_by_uid(uidb64)
    if user is None or not default_token_generator.check_token(user, token):
        return None
    return user


def reset_password(user, new_password):
    """Set the password and end all sessions that used the old one."""
    user.set_password(new_password)
    user.save(update_fields=["password"])
    blacklist_all_refresh_tokens(user)
