"""HTTP endpoints for registration, activation and the JWT cookie session."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.api.permissions import IsTrustedOrigin
from auth_app.api.serializers import LoginSerializer, RegistrationSerializer
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


class PublicAPIView(APIView):
    """Endpoint that must work without, or with stale, auth cookies."""

    authentication_classes = []
    permission_classes = [IsTrustedOrigin]

    def get_authenticate_header(self, request):
        """Keep HTTP 401 for invalid tokens; DRF sends 403 without it."""
        return 'Bearer realm="api"'


class RegisterView(PublicAPIView):

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = {"user": {"id": user.id, "email": user.email}}
        return Response(data, status=status.HTTP_201_CREATED)


class ActivateView(PublicAPIView):

    def get(self, request, uidb64, token):
        if activate_user(uidb64, token):
            return Response({"message": "Account successfully activated."})
        return Response(
            {"message": "Activation failed. The link is invalid or expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginView(PublicAPIView):

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

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE)
        if not raw_refresh:
            return Response(REFRESH_TOKEN_MISSING, status=400)
        access_token = refresh_access_token(raw_refresh)
        response = Response({"detail": "Token refreshed"})
        set_access_cookie(response, access_token)
        return response


class LogoutView(PublicAPIView):

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
