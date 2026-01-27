from django.contrib import admin

from .models import ProductCategory, Product, ProductPrice


class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 0


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant"]
    list_filter = ["tenant"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "tenant", "category", "type", "is_active"]
    list_filter = ["tenant", "category", "type", "is_active"]
    search_fields = ["name", "sku", "hubspot_id"]
    inlines = [ProductPriceInline]


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ["product", "price", "price_model", "valid_from", "valid_to"]
    list_filter = ["product__tenant", "price_model"]
    search_fields = ["product__name"]
