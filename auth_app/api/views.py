"""HTTP endpoints for registration, activation and the JWT cookie session."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.api.permissions import IsTrustedOrigin
from auth_app.api.serializers import (
    LoginSerializer,
    PasswordConfirmSerializer,
    PasswordResetSerializer,
    RegistrationSerializer,
)
from auth_app.services.password_reset_service import (
    get_user_for_reset,
    request_password_reset,
    reset_password,
)
from auth_app.services.registration_service import activate_user
from auth_app.services.session_service import (
    create_token_pair,
    logout_user,
    refresh_access_token,
)
from auth_app.utils import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    delete_auth_cookies,
    set_access_cookie,
    set_auth_cookies,
)

REFRESH_TOKEN_MISSING = {"detail": "Refresh token missing."}
INVALID_RESET_LINK = {"detail": "The reset link is invalid or has expired."}


class PublicAPIView(APIView):
    """Endpoint that must work without, or with stale, auth cookies."""

    authentication_classes = []
    permission_classes = [IsTrustedOrigin]

    def get_authenticate_header(self, request):
        """Keep HTTP 401 for invalid tokens; DRF sends 403 without it."""
        return 'Bearer realm="api"'


class RegisterView(PublicAPIView):
    """Create an inactive account and queue the activation email.

    Unlike the school docs, the response holds no activation token: a
    usable token would let anyone activate a foreign email address.
    """

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = {"user": {"id": user.id, "email": user.email}}
        return Response(data, status=status.HTTP_201_CREATED)


class ActivateView(PublicAPIView):
    """Activate an account; each link works once and expires after 24 h."""

    def get(self, request, uidb64, token):
        if activate_user(uidb64, token):
            return Response({"message": "Account successfully activated."})
        return Response(
            {"message": "Activation failed. The link is invalid or expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginView(PublicAPIView):
    """Log in with email and password and set both JWT cookies.

    Wrong passwords, unknown and inactive accounts get the same 400.
    """

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        response = Response({
            "detail": "Login successful",
            "user": {"id": user.id, "username": user.username},
        })
        set_auth_cookies(response, create_token_pair(user))
        return response


class TokenRefreshView(PublicAPIView):
    """The ``access`` field follows the school docs; clients use the cookie."""

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE)
        if not raw_refresh:
            return Response(REFRESH_TOKEN_MISSING, status=400)
        access_token = refresh_access_token(raw_refresh)
        response = Response(
            {"detail": "Token refreshed", "access": str(access_token)}
        )
        set_access_cookie(response, access_token)
        return response


class LogoutView(PublicAPIView):
    """Blacklist the refresh token, revoke the access token, drop cookies."""

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE)
        if not raw_refresh:
            return Response(REFRESH_TOKEN_MISSING, status=400)
        logout_user(raw_refresh, request.COOKIES.get(ACCESS_COOKIE))
        response = Response({
            "detail": "Logout successful! All tokens will be deleted. "
                      "Refresh token is now invalid."
        })
        delete_auth_cookies(response)
        return response


class PasswordResetView(PublicAPIView):
    """Same 200 answer for known and unknown addresses (no enumeration)."""

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "An email has been sent to reset your password."}
        )


class PasswordConfirmView(PublicAPIView):
    """Set a new password via a reset link and end all old sessions."""

    def post(self, request, uidb64, token):
        user = get_user_for_reset(uidb64, token)
        if user is None:
            return Response(INVALID_RESET_LINK, status=400)
        serializer = PasswordConfirmSerializer(
            data=request.data, context={"user": user}
        )
        serializer.is_valid(raise_exception=True)
        reset_password(user, serializer.validated_data["new_password"])
        return Response(
            {"detail": "Your Password has been successfully reset."}
        )
