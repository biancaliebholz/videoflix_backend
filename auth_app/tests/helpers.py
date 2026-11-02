"""Shared test data for the auth_app test suite."""

from auth_app.models import User

PASSWORD = "Sicher!Passwort2026"
FRONTEND_ORIGIN = "http://127.0.0.1:5500"


def create_user(email="max@example.com", is_active=True):
    return User.objects.create_user(email, PASSWORD, is_active=is_active)
