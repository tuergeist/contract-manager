"""Root GraphQL schema."""
import strawberry

from apps.core.schema import AuthMutation, CoreQuery, FeedbackMutation
from apps.tenants.schema import TenantQuery, TenantMutation
from apps.customers.schema import CustomerQuery, CustomerMutation
from apps.products.schema import ProductQuery
from apps.contracts.schema import (
    ContractQuery,
    ContractMutation,
    ContractImportQuery,
    ContractImportMutation,
)
from apps.invoices.schema import InvoiceQuery
from apps.audit.schema import AuditLogQuery
from apps.todos.schema import TodoQuery, TodoMutation


@strawberry.type
class Query(
    CoreQuery,
    TenantQuery,
    CustomerQuery,
    ProductQuery,
    ContractQuery,
    ContractImportQuery,
    InvoiceQuery,
    AuditLogQuery,
    TodoQuery,
):
    @strawberry.field
    def health(self) -> str:
        return "ok"


@strawberry.type
class Mutation(AuthMutation, FeedbackMutation, TenantMutation, CustomerMutation, ContractMutation, ContractImportMutation, TodoMutation):
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)
