from django.contrib import admin

from .models import Customer, CustomerNote


class CustomerNoteInline(admin.TabularInline):
    model = CustomerNote
    extra = 0
    readonly_fields = ["created_at", "user"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "hubspot_id", "is_active", "synced_at"]
    list_filter = ["tenant", "is_active"]
    search_fields = ["name", "hubspot_id"]
    inlines = [CustomerNoteInline]


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ["customer", "user", "created_at"]
    list_filter = ["customer__tenant"]
    search_fields = ["content", "customer__name"]
