## Why

Claude Desktop and claude.ai now support connecting to remote MCP servers via Settings > Connectors. Exposing contract-manager's data and actions as a remote MCP server lets users query contracts, customers, invoices, and products — and perform key actions like generating or voiding invoices — directly from Claude conversations, without switching to the web UI.

## What Changes

- New HTTP endpoint implementing the MCP remote server protocol (SSE transport with OAuth 2.1 authentication)
- Tools exposing read access to all core entities: customers, contracts, products, invoices (both generated and imported), bank transactions
- Tools exposing write actions: generate invoices, void invoices, send invoice emails, create/update contracts
- OAuth 2.1 flow so Claude Desktop can authenticate against contract-manager using existing user credentials
- Tool responses formatted as structured text summaries (not raw JSON) for natural conversation use

## Capabilities

### New Capabilities
- `mcp-server`: Remote MCP server endpoint with SSE transport, tool registration, OAuth 2.1 authentication, and tenant-scoped access control
- `mcp-tools`: Tool definitions for reading entities (customers, contracts, products, invoices, transactions) and performing actions (generate invoices, void, send email, create/update contracts)

### Modified Capabilities

_(none)_

## Impact

- **Backend**: New Django app or module for MCP server endpoint, OAuth provider flow, tool handlers
- **Dependencies**: MCP Python SDK (`mcp`), OAuth library for server-side flow
- **Auth**: New OAuth 2.1 authorization/token endpoints; existing JWT auth remains unchanged for the web UI
- **Security**: All tools must enforce the same RBAC permissions as the GraphQL mutations; tenant isolation must be maintained
- **Infrastructure**: SSE endpoint requires long-lived connections; may need reverse proxy configuration for production
