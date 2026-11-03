"""Validation of the authentication request payloads."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from auth_app.models import EMAIL_MAX_LENGTH, User
from auth_app.services.registration_service import register_user

GENERIC_ERROR = "Please check your input and try again."


def validate_password_strength(password, user, field="password"):
    """Run Django's password validators and report errors on ``field``."""
    try:
        validate_password(password, user)
    except DjangoValidationError as error:
        raise serializers.ValidationError({field: list(error.messages)})


class RegistrationSerializer(serializers.Serializer):
    """Payload of the school docs plus the frontend's optional checkbox.

    ``privacy_policy`` is not required, but must be true when it is sent.
    """

    email = serializers.EmailField(max_length=EMAIL_MAX_LENGTH)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirmed_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    privacy_policy = serializers.BooleanField(required=False, write_only=True)

    def validate_email(self, value):
        """Reject taken emails without revealing which accounts exist."""
        email = User.objects.normalize_email(value)
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(GENERIC_ERROR)
        return email

    def validate_privacy_policy(self, value):
        if not value:
            raise serializers.ValidationError(
                "Please accept the privacy policy."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"confirmed_password": "Passwords do not match."}
            )
        user = User(email=attrs["email"])
        validate_password_strength(attrs["password"], user)
        return attrs

    def create(self, validated_data):
        return register_user(
            validated_data["email"], validated_data["password"]
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        """Authenticate the user; unknown, wrong and inactive look the same."""
        user = authenticate(
            self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError({"detail": GENERIC_ERROR})
        attrs["user"] = user
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    """Expects the user of the reset link as ``context["user"]``."""

    new_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    confirm_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        validate_password_strength(
            attrs["new_password"], self.context["user"], field="new_password"
        )
        return attrs
