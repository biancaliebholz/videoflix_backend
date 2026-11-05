"""DRF authentication that reads the JWT from the HttpOnly access cookie."""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from auth_app.services.session_service import is_access_token_revoked
from auth_app.utils import ACCESS_COOKIE


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate requests via the ``access_token`` cookie.

    Returns ``None`` without a cookie so other endpoints stay anonymous and
    raises ``InvalidToken`` (HTTP 401) for invalid or revoked tokens.
    """

    def authenticate(self, request):
        """Return ``(user, token)`` from the cookie or ``None`` without it."""
        raw_token = request.COOKIES.get(ACCESS_COOKIE)
        if not raw_token:
            return None
        token = self.get_validated_token(raw_token)
        if is_access_token_revoked(token):
            raise InvalidToken("Token has been revoked.")
        return self.get_user(token), token
