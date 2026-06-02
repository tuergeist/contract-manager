"""Root GraphQL schema."""
import strawberry

from apps.core.schema import AuthMutation, CoreQuery, FeedbackMutation
from apps.tenants.schema import TenantQuery, TenantMutation
from apps.customers.schema import CustomerQuery, CustomerMutation
from apps.products.schema import ProductQuery, ProductMutation
from apps.contracts.schema import (
    ContractQuery,
    ContractMutation,
    ContractImportQuery,
    ContractImportMutation,
)
from apps.contracts.order_confirmation_schema import (
    OrderConfirmationQuery,
    OrderConfirmationMutation,
)
from apps.invoices.schema import InvoiceQuery, InvoiceMutation
from apps.invoices.dunning_schema import DunningQuery, DunningMutation
from apps.audit.schema import AuditLogQuery
from apps.todos.schema import TodoQuery, TodoMutation
from apps.banking.schema import BankingQuery, BankingMutation
from apps.offers.schema import OfferQuery, OfferMutation


@strawberry.type
class Query(
    CoreQuery,
    TenantQuery,
    CustomerQuery,
    ProductQuery,
    ContractQuery,
    ContractImportQuery,
    OrderConfirmationQuery,
    InvoiceQuery,
    DunningQuery,
    AuditLogQuery,
    TodoQuery,
    BankingQuery,
    OfferQuery,
):
    @strawberry.field
    def health(self) -> str:
        return "ok"


@strawberry.type
class Mutation(AuthMutation, FeedbackMutation, TenantMutation, CustomerMutation, ProductMutation, ContractMutation, ContractImportMutation, OrderConfirmationMutation, TodoMutation, InvoiceMutation, DunningMutation, BankingMutation, OfferMutation):
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)
