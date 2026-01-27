from django.contrib import admin

from .models import Contract, ContractItem, ContractAmendment


class ContractItemInline(admin.TabularInline):
    model = ContractItem
    extra = 0


class ContractAmendmentInline(admin.TabularInline):
    model = ContractAmendment
    extra = 0


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "tenant", "status", "start_date", "billing_interval"]
    list_filter = ["tenant", "status", "billing_interval"]
    search_fields = ["customer__name"]
    inlines = [ContractItemInline, ContractAmendmentInline]


@admin.register(ContractItem)
class ContractItemAdmin(admin.ModelAdmin):
    list_display = ["contract", "product", "quantity", "unit_price", "price_source"]
    list_filter = ["contract__tenant", "price_source"]
    search_fields = ["contract__customer__name", "product__name"]


@admin.register(ContractAmendment)
class ContractAmendmentAdmin(admin.ModelAdmin):
    list_display = ["contract", "type", "effective_date", "created_at"]
    list_filter = ["contract__tenant", "type"]
    search_fields = ["contract__customer__name", "description"]
