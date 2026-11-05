"""Small stateless helpers for tokens, links, cookies and request checks."""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from auth_app.models import User


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """Activation tokens that expire as soon as the account is active.

    The separate ``key_salt`` keeps activation and password reset tokens
    from being usable in each other's flow.
    """

    key_salt = "auth_app.utils.AccountActivationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        """Include ``is_active`` so a used activation link stops working."""
        return f"{super()._make_hash_value(user, timestamp)}{user.is_active}"


account_activation_token = AccountActivationTokenGenerator()


def encode_uid(user):
    """URL-safe base64 primary key as used in activation and reset links."""
    return urlsafe_base64_encode(force_bytes(user.pk))


def get_user_by_uid(uidb64):
    """Return the user for a base64 encoded primary key or ``None``."""
    try:
        user_id = int(force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError):
        return None
    return User.objects.filter(pk=user_id).first()


def build_frontend_link(page, uidb64, token):
    """Link to a school frontend page in ``pages/auth/`` with uid and token."""
    query = urlencode({"uid": uidb64, "token": token})
    return f"{settings.FRONTEND_URL}/pages/auth/{page}?{query}"


ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
AUTH_COOKIES = (ACCESS_COOKIE, REFRESH_COOKIE)


def set_access_cookie(response, access_token):
    lifetime = jwt_settings.ACCESS_TOKEN_LIFETIME
    _set_auth_cookie(response, ACCESS_COOKIE, access_token, lifetime)


def set_refresh_cookie(response, refresh_token):
    lifetime = jwt_settings.REFRESH_TOKEN_LIFETIME
    _set_auth_cookie(response, REFRESH_COOKIE, refresh_token, lifetime)


def set_auth_cookies(response, refresh_token):
    """Set both cookies from a simplejwt ``RefreshToken`` instance."""
    set_access_cookie(response, refresh_token.access_token)
    set_refresh_cookie(response, refresh_token)


def delete_auth_cookies(response):
    """Expire both cookies; path and SameSite must match the set cookies."""
    for name in AUTH_COOKIES:
        response.delete_cookie(
            name, path="/", samesite=settings.AUTH_COOKIE_SAMESITE
        )


def _set_auth_cookie(response, name, token, lifetime):
    """Host-only HttpOnly cookie; no ``Domain`` so it stays on the API host."""
    response.set_cookie(
        name,
        str(token),
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )


def has_auth_cookie(request):
    return any(name in request.COOKIES for name in AUTH_COOKIES)


def is_trusted_origin(origin):
    return origin in settings.CSRF_TRUSTED_ORIGINS
