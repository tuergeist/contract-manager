from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Tenant, Role, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "currency", "is_active", "created_at"]
    list_filter = ["is_active", "currency"]
    search_fields = ["name"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "is_default"]
    list_filter = ["tenant", "is_default"]
    search_fields = ["name", "tenant__name"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "tenant", "role", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff", "tenant"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Tenant", {"fields": ("tenant", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "tenant", "role")}),
    )
