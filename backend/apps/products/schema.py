"""GraphQL schema for products."""
from decimal import Decimal
import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info
from django.db.models import OuterRef, Subquery

from apps.core.context import Context
from apps.core.permissions import get_current_user, require_perm
from .models import Product, ProductCategory, ProductPrice


@strawberry_django.type(ProductCategory)
class ProductCategoryType:
    id: auto
    name: auto


@strawberry.type
class ProductPriceType:
    id: int
    price: Decimal
    valid_from: str
    valid_to: str | None


@strawberry_django.type(Product)
class ProductType:
    id: auto
    name: auto
    sku: auto
    description: auto
    type: auto
    billing_frequency: auto
    is_active: auto
    synced_at: auto
    category: ProductCategoryType | None

    @strawberry.field
    def current_price(self) -> ProductPriceType | None:
        price = ProductPrice.objects.filter(
            product=self,
            valid_to__isnull=True,
        ).first()
        if price:
            return ProductPriceType(
                id=price.id,
                price=price.price,
                valid_from=str(price.valid_from),
                valid_to=str(price.valid_to) if price.valid_to else None,
            )
        return None


@strawberry.type
class ProductConnection:
    """Paginated product list."""

    items: list[ProductType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool
    has_previous_page: bool


@strawberry.type
class ProductQuery:
    @strawberry.field
    def products(
        self,
        info: Info[Context, None],
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = "name",
        sort_order: str | None = "asc",
    ) -> ProductConnection:
        user = require_perm(info, "products", "read")
        if not user.tenant:
            return ProductConnection(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next_page=False,
                has_previous_page=False,
            )

        queryset = Product.objects.filter(tenant=user.tenant)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if search:
            queryset = queryset.filter(name__icontains=search)

        # Sorting
        allowed_sort_fields = {"name", "sku", "is_active", "synced_at", "price"}
        if sort_by == "price":
            # Annotate with current price for sorting
            current_price_subquery = ProductPrice.objects.filter(
                product=OuterRef("pk"),
                valid_to__isnull=True,
            ).values("price")[:1]
            queryset = queryset.annotate(current_price_value=Subquery(current_price_subquery))
            order_field = "-current_price_value" if sort_order == "desc" else "current_price_value"
            queryset = queryset.order_by(order_field)
        elif sort_by and sort_by in allowed_sort_fields:
            order_field = f"-{sort_by}" if sort_order == "desc" else sort_by
            queryset = queryset.order_by(order_field)
        else:
            queryset = queryset.order_by("name")

        total_count = queryset.count()

        # Calculate pagination
        offset = (page - 1) * page_size
        items = list(queryset[offset : offset + page_size])

        return ProductConnection(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=offset + page_size < total_count,
            has_previous_page=page > 1,
        )

    @strawberry.field
    def product(self, info: Info[Context, None], id: strawberry.ID) -> ProductType | None:
        user = require_perm(info, "products", "read")
        if user.tenant:
            return Product.objects.filter(tenant=user.tenant, id=id).first()
        return None
