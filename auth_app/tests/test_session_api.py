"""Tests for cookie authentication, token refresh and logout."""

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from auth_app.api.authentication import CookieJWTAuthentication
from auth_app.services.session_service import (
    blacklist_all_refresh_tokens,
    is_access_token_revoked,
    logout_user,
)
from auth_app.tests.helpers import FRONTEND_ORIGIN, create_user

LOCMEM_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class CookieSessionTestCase(APITestCase):
    """Logged-in client whose requests come from the frontend origin."""

    def setUp(self):
        self.user = create_user()
        self.refresh = RefreshToken.for_user(self.user)
        self.access = str(self.refresh.access_token)
        self.client.cookies["refresh_token"] = str(self.refresh)
        self.client.cookies["access_token"] = self.access

    def post(self, url_name):
        return self.client.post(
            reverse(url_name), format="json", HTTP_ORIGIN=FRONTEND_ORIGIN
        )


@override_settings(CACHES=LOCMEM_CACHE)
class CookieJWTAuthenticationTests(CookieSessionTestCase):

    def authenticate(self, cookies):
        request = APIRequestFactory().get("/")
        request.COOKIES.update(cookies)
        return CookieJWTAuthentication().authenticate(request)

    def test_valid_access_cookie_authenticates_user(self):
        user, token = self.authenticate({"access_token": self.access})
        self.assertEqual(user, self.user)

    def test_missing_cookie_means_anonymous(self):
        self.assertIsNone(self.authenticate({}))

    def test_invalid_or_revoked_token_raises_401(self):
        logout_user(str(self.refresh), self.access)
        for raw in ("garbage", self.access):
            with self.subTest(raw=raw[:10]), self.assertRaises(InvalidToken):
                self.authenticate({"access_token": raw})

    def test_unauthenticated_header_triggers_401_not_403(self):
        header = CookieJWTAuthentication().authenticate_header(None)
        self.assertTrue(header)


class TokenRefreshApiTests(CookieSessionTestCase):

    def test_valid_refresh_cookie_sets_new_access_cookie(self):
        response = self.post("token_refresh")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"detail": "Token refreshed"})
        new_access = response.cookies["access_token"]
        self.assertTrue(new_access["httponly"])
        user_id = AccessToken(new_access.value)["user_id"]
        self.assertEqual(user_id, str(self.user.id))

    def test_missing_refresh_cookie_returns_400(self):
        del self.client.cookies["refresh_token"]
        self.assertEqual(self.post("token_refresh").status_code, 400)

    def test_invalid_refresh_cookie_returns_401(self):
        self.client.cookies["refresh_token"] = "garbage"
        self.assertEqual(self.post("token_refresh").status_code, 401)

    def test_blacklisted_refresh_token_returns_401(self):
        self.refresh.blacklist()
        self.assertEqual(self.post("token_refresh").status_code, 401)

    def test_inactive_user_cannot_refresh(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.post("token_refresh").status_code, 401)

    def test_expired_access_cookie_does_not_block_refresh(self):
        self.client.cookies["access_token"] = "expired"
        self.assertEqual(self.post("token_refresh").status_code, 200)


@override_settings(CACHES=LOCMEM_CACHE)
class LogoutApiTests(CookieSessionTestCase):

    def test_logout_returns_documented_message(self):
        response = self.post("logout")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["detail"],
            "Logout successful! All tokens will be deleted. "
            "Refresh token is now invalid.",
        )

    def test_logout_deletes_both_cookies(self):
        cookies = self.post("logout").cookies
        for name in ("access_token", "refresh_token"):
            self.assertEqual(cookies[name].value, "")
            self.assertEqual(cookies[name]["max-age"], 0)

    def test_refresh_token_is_blacklisted(self):
        self.post("logout")
        jti = self.refresh["jti"]
        blacklisted = BlacklistedToken.objects.filter(token__jti=jti)
        self.assertTrue(blacklisted.exists())

    def test_still_valid_access_token_is_revoked(self):
        self.post("logout")
        self.assertTrue(is_access_token_revoked(AccessToken(self.access)))

    def test_old_tokens_are_rejected_after_logout(self):
        self.post("logout")
        self.client.cookies["refresh_token"] = str(self.refresh)
        self.client.cookies["access_token"] = self.access
        self.assertEqual(self.post("token_refresh").status_code, 401)

    def test_missing_refresh_cookie_returns_400(self):
        del self.client.cookies["refresh_token"]
        self.assertEqual(self.post("logout").status_code, 400)

    def test_invalid_tokens_still_log_out(self):
        self.client.cookies["refresh_token"] = "garbage"
        self.client.cookies["access_token"] = "garbage"
        self.assertEqual(self.post("logout").status_code, 200)


class BlacklistAllTokensTests(CookieSessionTestCase):

    def test_all_outstanding_refresh_tokens_are_blacklisted(self):
        second = RefreshToken.for_user(self.user)
        blacklist_all_refresh_tokens(self.user)
        for token in (self.refresh, second):
            with self.subTest(jti=token["jti"]):
                self.assertTrue(
                    BlacklistedToken.objects.filter(
                        token__jti=token["jti"]
                    ).exists()
                )
