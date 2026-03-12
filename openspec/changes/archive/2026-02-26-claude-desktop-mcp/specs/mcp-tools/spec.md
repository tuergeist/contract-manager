## ADDED Requirements

### Requirement: Customer read tools
The system SHALL provide MCP tools `list_customers` and `get_customer`. `list_customers` SHALL accept optional `search` (text), `offset`, and `limit` parameters, returning a text summary of matching customers with name, company, email, and contract count. `get_customer` SHALL accept a `customer_id` and return detailed customer information including contacts, billing emails, and linked contracts.

#### Scenario: List customers with search
- **WHEN** a user calls `list_customers` with `search: "Acme"`
- **THEN** the tool returns a text summary of customers matching "Acme", paginated by `limit` (default 20)

#### Scenario: Get customer details
- **WHEN** a user calls `get_customer` with a valid `customer_id`
- **THEN** the tool returns customer name, company, contacts, billing emails, and a list of contract summaries

#### Scenario: Customer not found
- **WHEN** a user calls `get_customer` with a non-existent `customer_id`
- **THEN** the tool returns a text message indicating the customer was not found

### Requirement: Contract read tools
The system SHALL provide MCP tools `list_contracts` and `get_contract`. `list_contracts` SHALL accept optional `status`, `customer_id`, `search`, `offset`, and `limit` parameters. `get_contract` SHALL return contract details including status, customer, billing cycle, items (recurring and one-off), and financial summary (MRR, total).

#### Scenario: List contracts filtered by status
- **WHEN** a user calls `list_contracts` with `status: "active"`
- **THEN** the tool returns a paginated text summary of active contracts

#### Scenario: Get contract with items
- **WHEN** a user calls `get_contract` with a valid `contract_id`
- **THEN** the tool returns contract metadata, customer info, all line items grouped by recurring/one-off, and financial totals

### Requirement: Product read tools
The system SHALL provide MCP tools `list_products` and `get_product`. `list_products` SHALL accept optional `search`, `offset`, and `limit` parameters. Products SHALL show name, SKU, default price, and billing cycle.

#### Scenario: List products
- **WHEN** a user calls `list_products`
- **THEN** the tool returns a paginated text summary of all products

### Requirement: Invoice read tools
The system SHALL provide MCP tools `list_invoices` and `get_invoice`. `list_invoices` SHALL accept optional `customer_id`, `status`, `date_from`, `date_to`, `offset`, and `limit` parameters. The tool SHALL cover both generated (`InvoiceRecord`) and imported (`ImportedInvoice`) invoices. `get_invoice` SHALL return full invoice details including line items, amounts, email status, and PDF availability.

#### Scenario: List invoices for a customer
- **WHEN** a user calls `list_invoices` with `customer_id: 42`
- **THEN** the tool returns a paginated list of all invoices (generated and imported) for that customer

#### Scenario: Get invoice details
- **WHEN** a user calls `get_invoice` with a valid invoice identifier
- **THEN** the tool returns invoice number, date, customer, status, line items, net/gross totals, and email send status

### Requirement: Bank transaction read tools
The system SHALL provide MCP tools `list_transactions` and `get_transaction`. `list_transactions` SHALL accept optional `counterparty`, `date_from`, `date_to`, `offset`, and `limit` parameters. Transactions SHALL show date, amount, counterparty, and matching status.

#### Scenario: List transactions with date filter
- **WHEN** a user calls `list_transactions` with `date_from: "2025-01-01"` and `date_to: "2025-01-31"`
- **THEN** the tool returns a paginated list of transactions in that date range

### Requirement: Generate invoices tool
The system SHALL provide an MCP tool `generate_invoices` that triggers invoice generation for a given contract and billing period. The tool SHALL accept `contract_id` and `billing_date` parameters. It SHALL use the existing `InvoiceService` to generate invoices and return a summary of what was generated.

#### Scenario: Generate invoices for a contract
- **WHEN** a user with `invoices.generate` permission calls `generate_invoices` with `contract_id` and `billing_date`
- **THEN** the system generates invoice records for the contract's billing period and returns a summary with invoice numbers and amounts

#### Scenario: No items to invoice
- **WHEN** a user calls `generate_invoices` for a contract with no billable items in the period
- **THEN** the tool returns a message indicating no invoices were generated

### Requirement: Void invoice tool
The system SHALL provide an MCP tool `void_invoice` that voids a generated invoice record. The tool SHALL accept `invoice_id` and optional `reason` parameters. It SHALL use the existing void logic and return confirmation.

#### Scenario: Void an invoice
- **WHEN** a user with `invoices.write` permission calls `void_invoice` with a valid `invoice_id`
- **THEN** the invoice status is set to voided and the tool returns confirmation with the invoice number

#### Scenario: Void already-voided invoice
- **WHEN** a user calls `void_invoice` on an invoice that is already voided
- **THEN** the tool returns an error message indicating the invoice is already voided

### Requirement: Send invoice email tool
The system SHALL provide an MCP tool `send_invoice_email` that sends a generated invoice to the customer's billing email addresses. The tool SHALL accept an `invoice_id` parameter and use the existing email sending logic. It SHALL return the recipient list on success.

#### Scenario: Send invoice email
- **WHEN** a user with `invoices.write` permission calls `send_invoice_email` with a valid `invoice_id`
- **THEN** the system queues the email for sending and returns the recipient list

#### Scenario: No billing emails configured
- **WHEN** a user calls `send_invoice_email` for an invoice whose customer has no billing emails
- **THEN** the tool returns an error message indicating no billing email addresses are configured

### Requirement: Create and update contract tools
The system SHALL provide MCP tools `create_contract` and `update_contract`. `create_contract` SHALL accept customer_id, name, billing_cycle, and start_date, creating a draft contract. `update_contract` SHALL accept contract_id and optional fields to update (name, status, billing_cycle, notes). Both SHALL return the updated contract summary.

#### Scenario: Create a draft contract
- **WHEN** a user with `contracts.write` permission calls `create_contract` with required fields
- **THEN** a new draft contract is created and the tool returns its details

#### Scenario: Update contract status
- **WHEN** a user with `contracts.write` permission calls `update_contract` with `contract_id` and `status: "active"`
- **AND** the contract is currently in draft status
- **THEN** the contract status is updated to active and the tool returns confirmation

#### Scenario: Invalid status transition
- **WHEN** a user calls `update_contract` with an invalid status transition (e.g., draft → cancelled)
- **THEN** the tool returns an error message describing the valid transitions

### Requirement: Tool responses as structured text
All MCP tools SHALL return responses as human-readable structured text suitable for conversation. List tools SHALL include item counts and pagination info. Detail tools SHALL format data with labels and values. Error responses SHALL be clear text messages, not JSON error objects.

#### Scenario: List response format
- **WHEN** a list tool returns results
- **THEN** the response includes a header with total count, formatted items, and pagination info (e.g., "Showing 1-20 of 45 customers")

#### Scenario: Error response format
- **WHEN** a tool encounters an error (not found, permission denied, validation failure)
- **THEN** the response is a clear text message describing the error
