## Context

Contract-manager is a Django 5 + Strawberry-GraphQL app with JWT-based auth (HS256, 24h access / 7d refresh tokens). Users authenticate with email/password, and all data is tenant-scoped. The frontend is a React SPA talking to `/graphql`. RBAC permissions are checked via `require_perm(info, resource, action)` helpers.

Claude Desktop and claude.ai support remote MCP servers via Streamable HTTP transport with OAuth 2.1 authentication. The MCP Python SDK (`mcp` package) provides `FastMCP` for building servers, and `django-mcp-server` wraps this for Django integration.

## Goals / Non-Goals

**Goals:**
- Expose contract-manager data and actions as MCP tools usable from Claude Desktop / claude.ai
- Authenticate via OAuth 2.1 (authorization code + PKCE) reusing existing user credentials
- Enforce the same RBAC permissions and tenant isolation as the web UI
- Support Streamable HTTP transport at a single `/mcp` endpoint

**Non-Goals:**
- Replacing or modifying the existing JWT auth flow for the web frontend
- Supporting stdio or other non-HTTP transports
- Exposing admin/superuser operations (user management, tenant settings)
- Real-time subscriptions or long-running streaming tools
- Building a custom OAuth server from scratch (use `django-oauth-toolkit`)

## Decisions

### 1. Use `django-mcp-server` + `django-oauth-toolkit`

**Choice:** Use the `django-mcp-server` package for MCP protocol handling and `django-oauth-toolkit` (DOT) for OAuth 2.1.

**Why:** `django-mcp-server` is a validated Claude AI remote integration that handles Streamable HTTP transport, tool registration, and JSON-RPC message routing. DOT is the established Django OAuth provider with PKCE support, token management, and metadata discovery.

**Alternatives considered:**
- Raw `mcp` SDK + custom ASGI app: More control but significant boilerplate for transport, session management, and OAuth endpoints
- Custom OAuth implementation: High risk of security issues, unnecessary when DOT exists

### 2. New Django app `apps.mcp`

**Choice:** Create a dedicated `apps.mcp` Django app containing tool definitions and MCP configuration.

**Why:** Keeps MCP concerns separate from existing GraphQL schema. Tools call into existing service functions and querysets rather than duplicating business logic.

### 3. OAuth 2.1 with authorization code + PKCE

**Choice:** Authorization code grant with PKCE for Claude Desktop authentication. Users log in with their existing email/password through Django's auth, then authorize the MCP client.

**Why:** MCP spec requires OAuth 2.1. PKCE is mandatory for public clients (Claude Desktop). Reusing Django's auth backend means no separate credential store.

**Flow:**
1. Claude Desktop discovers `/.well-known/oauth-authorization-server` metadata
2. Dynamic client registration via `/oauth/register/` (or pre-registered client)
3. User redirected to `/oauth/authorize/` → logs in with existing credentials → grants access
4. Claude Desktop exchanges auth code for access token at `/oauth/token/`
5. All MCP requests include `Authorization: Bearer <token>`

### 4. Tool design: text summaries, not raw JSON

**Choice:** Tools return structured text (markdown-like) summaries rather than raw JSON or model serializations.

**Why:** MCP tool responses appear in natural language conversations. Readable summaries are more useful than raw data dumps. Pagination via offset/limit parameters for list tools.

### 5. Permission mapping

**Choice:** Each MCP tool checks permissions using the same `check_perm` helpers as GraphQL mutations. The authenticated OAuth user's tenant and roles determine access.

**Mapping:**
| MCP Tool | Permission Required |
|---|---|
| list/get customers | `customers.read` |
| list/get contracts | `contracts.read` |
| list/get products | `products.read` |
| list/get invoices | `invoices.read` |
| list/get transactions | `banking.read` |
| generate invoices | `invoices.generate` |
| void invoice | `invoices.write` |
| send invoice email | `invoices.write` |
| create/update contract | `contracts.write` |

### 6. Tenant resolution from OAuth token

**Choice:** Resolve tenant from the authenticated user's `user.tenant` field (same as `TenantMiddleware` does for web requests). All queries are scoped to this tenant.

**Why:** Consistent with existing multi-tenant architecture. No additional tenant selection needed.

## Risks / Trade-offs

**SSE / long-lived connections in production** → The Streamable HTTP transport may use SSE for streaming responses. Nginx/reverse proxy config may need `proxy_buffering off` and increased timeouts. Mitigate by testing with production proxy config and documenting required settings.

**OAuth token storage** → DOT stores tokens in the database. For a small-user deployment this is fine. If token volume becomes an issue, DOT supports customizable token backends.

**django-mcp-server maturity** → Package is relatively new (v0.5.x). Pin version and monitor for breaking changes. Fallback: the underlying `mcp` SDK is stable, and we can implement the transport layer directly if needed.

**ASGI requirement** → `django-mcp-server` with Streamable HTTP may require ASGI (for SSE streaming). Production currently uses gunicorn with gthread workers. May need to run the MCP endpoint under an ASGI server (uvicorn/daphne) alongside the existing WSGI app, or switch gunicorn to uvicorn workers for the MCP path. Investigate during implementation.

**Tool explosion** → Starting with ~10 tools (5 read + 5 write). Keep focused on high-value actions. Can add more tools incrementally without protocol changes.
