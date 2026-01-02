from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile, Social, SocialLink, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "email_verified",
        "mfa_enabled",
        "is_active",
        "is_staff",
    )
    list_filter = ("is_staff", "is_active", "email_verified", "mfa_enabled")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        ("Verification", {"fields": ("email_verified", "mfa_enabled")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "profession", "gender", "show_location", "last_seen")
    list_filter = ("gender", "show_location")
    search_fields = ("user__email", "user__first_name", "user__last_name", "profession")
    readonly_fields = ("last_location_update", "last_seen")


@admin.register(Social)
class SocialAdmin(admin.ModelAdmin):
    list_display = ("user", "adventures", "places_visited", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("friends",)


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "url", "created_at")
    list_filter = ("platform",)
    search_fields = ("user__email", "platform")
