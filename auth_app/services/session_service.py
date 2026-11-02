"""JWT session handling: issuing, refreshing and revoking tokens."""

import time

from django.contrib.auth.models import update_last_login
from django.core.cache import cache
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

REVOKED_ACCESS_KEY = "revoked-access-token:{jti}"


def create_token_pair(user):
    update_last_login(None, user)
    return RefreshToken.for_user(user)


def refresh_access_token(raw_refresh):
    """Return a new access token.

    Raises ``InvalidToken`` (HTTP 401) for invalid, expired or blacklisted
    refresh tokens and ``AuthenticationFailed`` for inactive users.
    """
    serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
    try:
        serializer.is_valid(raise_exception=True)
    except TokenError as error:
        raise InvalidToken(error.args[0]) from error
    return serializer.validated_data["access"]


def logout_user(raw_refresh, raw_access=None):
    """Blacklist the refresh token and revoke the still valid access token.

    Access JWTs are stateless, so their ``jti`` is stored in the cache until
    the token would expire anyway. Invalid tokens are ignored on purpose:
    logging out must always succeed.
    """
    _blacklist_refresh_token(raw_refresh)
    if raw_access:
        _revoke_access_token(raw_access)


def is_access_token_revoked(access_token):
    key = REVOKED_ACCESS_KEY.format(jti=access_token["jti"])
    return cache.get(key) is not None


def blacklist_all_refresh_tokens(user):
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def _blacklist_refresh_token(raw_refresh):
    try:
        RefreshToken(raw_refresh).blacklist()
    except TokenError:
        pass


def _revoke_access_token(raw_access):
    try:
        token = AccessToken(raw_access)
    except TokenError:
        return
    remaining_seconds = max(int(token["exp"] - time.time()), 1)
    key = REVOKED_ACCESS_KEY.format(jti=token["jti"])
    cache.set(key, True, timeout=remaining_seconds)
