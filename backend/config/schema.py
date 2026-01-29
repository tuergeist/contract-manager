"""Root GraphQL schema."""
import strawberry

from apps.core.schema import AuthMutation, CoreQuery
from apps.tenants.schema import TenantQuery, TenantMutation
from apps.customers.schema import CustomerQuery
from apps.products.schema import ProductQuery
from apps.contracts.schema import (
    ContractQuery,
    ContractMutation,
    ContractImportQuery,
    ContractImportMutation,
)


@strawberry.type
class Query(
    CoreQuery,
    TenantQuery,
    CustomerQuery,
    ProductQuery,
    ContractQuery,
    ContractImportQuery,
):
    @strawberry.field
    def health(self) -> str:
        return "ok"


@strawberry.type
class Mutation(AuthMutation, TenantMutation, ContractMutation, ContractImportMutation):
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)
