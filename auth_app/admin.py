"""Django admin configuration for the email-based user model."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from auth_app.models import User

PERMISSION_FIELDS = (
    "is_active", "is_staff", "is_superuser", "groups", "user_permissions",
)
ADD_FIELDS = ("email", "username", "usable_password", "password1", "password2")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for users that log in with their email address."""

    ordering = ("email",)
    list_display = ("email", "username", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {
            "fields": ("username", "first_name", "last_name"),
        }),
        (_("Permissions"), {"fields": PERMISSION_FIELDS}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ADD_FIELDS}),)
