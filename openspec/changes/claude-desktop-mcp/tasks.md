## 1. Dependencies & Django App Setup

- [x] 1.1 Add `django-oauth-toolkit` and `django-mcp-server` to `pyproject.toml` dependencies
- [x] 1.2 Create `backend/apps/mcp/` Django app with `__init__.py`, `apps.py`
- [x] 1.3 Add `oauth2_provider` and `mcp_server` and `apps.mcp` to `INSTALLED_APPS` in `base.py`
- [x] 1.4 Configure `django-oauth-toolkit` settings (PKCE required, token expiration, scopes)
- [x] 1.5 Run `makemigrations` and `migrate` for oauth2_provider tables

## 2. OAuth 2.1 Endpoints

- [x] 2.1 Add OAuth URL routes: `/oauth/authorize/`, `/oauth/token/`, `/oauth/register/` in `config/urls.py`
- [x] 2.2 Implement `/.well-known/oauth-authorization-server` metadata discovery endpoint
- [x] 2.3 Configure dynamic client registration (RFC 7591) via DOT
- [x] 2.4 Verify OAuth authorization code + PKCE flow works end-to-end with a test client

## 3. MCP Server Endpoint

- [x] 3.1 Configure `django-mcp-server` with Streamable HTTP transport at `/mcp`
- [x] 3.2 Wire OAuth Bearer token authentication into MCP endpoint (DOT token validation)
- [x] 3.3 Implement tenant resolution from authenticated OAuth user
- [x] 3.4 Add RBAC permission check helper that wraps existing `check_perm` for MCP tool context

## 4. Read Tools — Customers & Products

- [x] 4.1 Implement `list_customers` tool (search, offset, limit, text summary response)
- [x] 4.2 Implement `get_customer` tool (customer details, contacts, billing emails, contracts)
- [x] 4.3 Implement `list_products` tool (search, offset, limit)
- [x] 4.4 Implement `get_product` tool (product details, pricing, billing cycle)

## 5. Read Tools — Contracts & Invoices

- [x] 5.1 Implement `list_contracts` tool (status, customer_id, search, offset, limit)
- [x] 5.2 Implement `get_contract` tool (details, items grouped recurring/one-off, financial summary)
- [x] 5.3 Implement `list_invoices` tool (customer_id, status, date_from, date_to — covers both InvoiceRecord and ImportedInvoice)
- [x] 5.4 Implement `get_invoice` tool (invoice details, line items, amounts, email status)

## 6. Read Tools — Banking

- [x] 6.1 Implement `list_transactions` tool (counterparty, date_from, date_to, offset, limit)
- [x] 6.2 Implement `get_transaction` tool (transaction details, matching status)

## 7. Write Tools

- [x] 7.1 Implement `generate_invoices` tool (contract_id, billing_date → InvoiceService)
- [x] 7.2 Implement `void_invoice` tool (invoice_id, optional reason)
- [x] 7.3 Implement `send_invoice_email` tool (invoice_id → queue email task)
- [x] 7.4 Implement `create_contract` tool (customer_id, name, billing_cycle, start_date → draft)
- [x] 7.5 Implement `update_contract` tool (contract_id, optional fields, status transitions)

## 8. Production & Deployment

- [x] 8.1 Add `django-oauth-toolkit` and `django-mcp-server` to `Dockerfile.prod` dependencies
- [x] 8.2 Investigate ASGI requirement for SSE streaming; update gunicorn config or add uvicorn if needed
- [x] 8.3 Document reverse proxy config for SSE (nginx `proxy_buffering off`, timeout settings)
- [x] 8.4 Add MCP server URL to `docker-compose.prod.yml` environment / docs

## 9. Testing

- [x] 9.1 Write tests for OAuth flow (metadata discovery, authorization, token exchange)
- [x] 9.2 Write tests for tenant resolution and RBAC permission checks on MCP tools
- [x] 9.3 Write tests for each read tool (list/get customers, contracts, products, invoices, transactions)
- [x] 9.4 Write tests for each write tool (generate, void, send email, create/update contract)
- [ ] 9.5 End-to-end test: connect Claude Desktop to local MCP server and verify tool execution
