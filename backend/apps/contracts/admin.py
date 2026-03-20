from django.contrib import admin

from .models import Contract, ContractItem, ContractAmendment, RevenueGoal, NewBusinessGoal, AutoLinkRule, Department, DepartmentServiceMapping, AbsenceReport, AbsenceReportEntry


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


@admin.register(RevenueGoal)
class RevenueGoalAdmin(admin.ModelAdmin):
    list_display = ["year", "revenue_type", "target_amount", "tenant"]
    list_filter = ["tenant", "year", "revenue_type"]


@admin.register(NewBusinessGoal)
class NewBusinessGoalAdmin(admin.ModelAdmin):
    list_display = ["year", "goal_type", "target_amount", "tenant"]
    list_filter = ["tenant", "year", "goal_type"]


@admin.register(AutoLinkRule)
class AutoLinkRuleAdmin(admin.ModelAdmin):
    list_display = ["pattern", "match_type", "contract", "is_active", "tenant"]
    list_filter = ["tenant", "match_type", "is_active"]
    search_fields = ["pattern", "contract__customer__name"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "tenant"]
    list_filter = ["tenant"]
    search_fields = ["name"]


@admin.register(DepartmentServiceMapping)
class DepartmentServiceMappingAdmin(admin.ModelAdmin):
    list_display = ["external_service_name", "department", "tenant"]
    list_filter = ["tenant", "department"]
    search_fields = ["external_service_name"]


class AbsenceReportEntryInline(admin.TabularInline):
    model = AbsenceReportEntry
    extra = 0


@admin.register(AbsenceReport)
class AbsenceReportAdmin(admin.ModelAdmin):
    list_display = ["year", "month", "status", "tenant", "finalized_at"]
    list_filter = ["tenant", "status", "year"]
    inlines = [AbsenceReportEntryInline]
