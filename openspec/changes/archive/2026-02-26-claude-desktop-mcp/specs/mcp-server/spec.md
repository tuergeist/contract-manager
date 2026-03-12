## ADDED Requirements

### Requirement: MCP endpoint with Streamable HTTP transport
The system SHALL expose a single HTTP endpoint at `/mcp` implementing the MCP Streamable HTTP transport protocol. The endpoint SHALL accept POST requests with JSON-RPC messages and return either `application/json` or `text/event-stream` responses. The endpoint SHALL accept GET requests for SSE streaming from the server.

#### Scenario: Client sends initialization request
- **WHEN** a client POSTs a JSON-RPC `InitializeRequest` to `/mcp`
- **THEN** the server returns an `InitializeResult` with server capabilities and an `Mcp-Session-Id` header

#### Scenario: Client sends tool call
- **WHEN** an authenticated client POSTs a JSON-RPC tool call request to `/mcp`
- **THEN** the server executes the tool and returns the result as a JSON-RPC response

#### Scenario: Unauthenticated request
- **WHEN** a client sends a request to `/mcp` without a valid Bearer token
- **THEN** the server returns HTTP 401 Unauthorized

### Requirement: OAuth 2.1 authentication with authorization code + PKCE
The system SHALL implement OAuth 2.1 authorization code grant with PKCE using `django-oauth-toolkit`. Users SHALL authenticate with their existing email/password credentials. The system SHALL expose the following endpoints: authorization (`/oauth/authorize/`), token exchange (`/oauth/token/`), and metadata discovery (`/.well-known/oauth-authorization-server`).

#### Scenario: OAuth metadata discovery
- **WHEN** a client GETs `/.well-known/oauth-authorization-server`
- **THEN** the server returns a JSON metadata document with `authorization_endpoint`, `token_endpoint`, and `registration_endpoint` URLs

#### Scenario: Authorization code flow with PKCE
- **WHEN** a client redirects a user to `/oauth/authorize/` with a `code_challenge` parameter
- **AND** the user logs in with valid credentials and grants access
- **THEN** the server redirects back with an authorization code
- **AND** the client exchanges the code + `code_verifier` at `/oauth/token/` for an access token

#### Scenario: Invalid PKCE verifier
- **WHEN** a client exchanges an authorization code with an incorrect `code_verifier`
- **THEN** the server returns an OAuth error and does not issue a token

### Requirement: Dynamic client registration
The system SHALL support OAuth 2.0 Dynamic Client Registration (RFC 7591) at `/oauth/register/`. MCP clients SHALL be able to register themselves to obtain a `client_id` without manual configuration.

#### Scenario: Client registers dynamically
- **WHEN** a new MCP client POSTs a registration request to `/oauth/register/` with `redirect_uris` and `client_name`
- **THEN** the server returns a `client_id` and registration metadata

### Requirement: Tenant-scoped access from OAuth token
The system SHALL resolve the tenant from the authenticated OAuth user's `tenant` field. All MCP tool queries and actions SHALL be scoped to this tenant. Users without an active tenant SHALL be denied access.

#### Scenario: Tenant resolution
- **WHEN** an authenticated user calls an MCP tool
- **THEN** all data queries and mutations are scoped to the user's tenant

#### Scenario: User without active tenant
- **WHEN** a user whose tenant is inactive authenticates via OAuth
- **AND** the user calls an MCP tool
- **THEN** the server returns an error indicating the tenant is not active

### Requirement: RBAC permission enforcement
The system SHALL enforce the same RBAC permissions for MCP tools as for GraphQL mutations. Each tool SHALL check the authenticated user's permissions before executing. Unauthorized tool calls SHALL return an error message, not an HTTP error.

#### Scenario: User with sufficient permissions
- **WHEN** a user with `invoices.generate` permission calls the generate-invoice tool
- **THEN** the tool executes successfully

#### Scenario: User without sufficient permissions
- **WHEN** a user without `invoices.generate` permission calls the generate-invoice tool
- **THEN** the tool returns a text error message indicating insufficient permissions
