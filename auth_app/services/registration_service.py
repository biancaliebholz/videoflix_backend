"""Registration and email activation of user accounts."""

from django.db import transaction

from auth_app.models import User
from auth_app.tasks import queue_activation_email
from auth_app.utils import account_activation_token, get_user_by_uid


def register_user(email, password):
    """Create an inactive user and queue the activation email.

    The email job is queued only after the transaction commits, so the
    worker never looks up a user that does not exist yet.
    """
    user = User.objects.create_user(email=email, password=password)
    transaction.on_commit(lambda: queue_activation_email(user.pk))
    return user


def activate_user(uidb64, token):
    """Activate the account behind a link; return ``False`` if invalid."""
    user = get_user_by_uid(uidb64)
    if user is None or not account_activation_token.check_token(user, token):
        return False
    user.is_active = True
    user.save(update_fields=["is_active"])
    return True
