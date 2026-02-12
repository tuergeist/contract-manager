## ADDED Requirements

### Requirement: Customer stores billing email addresses
The system SHALL store a list of billing email addresses for each customer.

#### Scenario: Customer with billing emails
- **WHEN** a customer has billing_emails ["billing@acme.com", "finance@acme.com"]
- **THEN** system displays these emails in the customer detail view

#### Scenario: Customer with no billing emails
- **WHEN** a customer has empty billing_emails
- **THEN** system shows no billing contacts section or an empty state

### Requirement: Receiver emails transfer to customer on invoice confirmation
The system SHALL merge invoice receiver emails into the customer's billing_emails when the customer is confirmed on an invoice.

#### Scenario: Transfer new emails to customer
- **WHEN** user confirms customer "Acme Corp" on an invoice with receiver_emails ["new@acme.com"]
- **THEN** system adds "new@acme.com" to Acme Corp's billing_emails if not already present

#### Scenario: Avoid duplicate emails
- **WHEN** invoice has receiver_emails ["billing@acme.com"] and customer already has billing_emails ["billing@acme.com", "other@acme.com"]
- **THEN** system does not add duplicate, customer keeps ["billing@acme.com", "other@acme.com"]

#### Scenario: Case-insensitive deduplication
- **WHEN** invoice has receiver_emails ["Billing@Acme.com"] and customer has ["billing@acme.com"]
- **THEN** system treats them as duplicates (no addition)

### Requirement: User can manage customer billing emails
The system SHALL allow users to add and remove billing email addresses from a customer.

#### Scenario: Add billing email manually
- **WHEN** user adds "accounts@acme.com" to customer's billing emails
- **THEN** system appends the email to billing_emails list

#### Scenario: Remove billing email
- **WHEN** user removes "old@acme.com" from customer's billing emails
- **THEN** system removes the email from billing_emails list

#### Scenario: Validate email format
- **WHEN** user attempts to add "not-an-email" as billing email
- **THEN** system rejects with error "Invalid email format"
