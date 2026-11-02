"""CSRF protection for the cookie based JWT authentication."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from auth_app.utils import has_auth_cookie, is_trusted_origin


class IsTrustedOrigin(BasePermission):
    """Allow unsafe requests only from trusted frontend origins.

    Browsers attach the auth cookies automatically, so a foreign site could
    otherwise trigger requests in the user's name. Browsers always send an
    ``Origin`` header with cross-origin requests; a request that carries auth
    cookies without one is rejected. Requests without cookies and without
    ``Origin`` (e.g. curl, Postman) stay possible.
    """

    message = "Request origin is not allowed."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        origin = request.headers.get("Origin")
        if origin is None:
            return not has_auth_cookie(request)
        return is_trusted_origin(origin)
