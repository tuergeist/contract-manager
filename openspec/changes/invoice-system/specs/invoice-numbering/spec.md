## ADDED Requirements

### Requirement: User can configure an invoice number scheme

The system SHALL allow users to define a number pattern for invoice numbering using placeholders.

#### Scenario: Define a number pattern
- **WHEN** user navigates to `/settings/invoice-numbering`
- **AND** enters a pattern such as `RE-{YYYY}-{NNNN}`
- **THEN** system stores the pattern as the active number scheme

#### Scenario: Supported placeholders
- **WHEN** user defines a pattern
- **THEN** system SHALL support these placeholders:
  - `{YYYY}` — 4-digit year (e.g., 2026)
  - `{YY}` — 2-digit year (e.g., 26)
  - `{MM}` — 2-digit month (e.g., 02)
  - `{NNN}` — 3-digit zero-padded counter
  - `{NNNN}` — 4-digit zero-padded counter
  - `{NNNNN}` — 5-digit zero-padded counter
- **AND** static text (letters, digits, hyphens, slashes) is allowed between placeholders

#### Scenario: Pattern preview
- **WHEN** user enters or modifies the pattern
- **THEN** system displays a live preview showing what the next invoice number would look like (e.g., `RE-2026-0001`)

#### Scenario: Pattern validation
- **WHEN** user enters a pattern without any counter placeholder (`{NNN}`, `{NNNN}`, `{NNNNN}`)
- **THEN** system shows a validation error: a counter placeholder is required

#### Scenario: Default pattern when none configured
- **WHEN** no number scheme has been configured
- **THEN** system uses default pattern `{YYYY}-{NNNN}` with counter starting at 1

### Requirement: User can configure counter reset rules

The system SHALL allow users to define when the counter resets.

#### Scenario: Yearly reset
- **WHEN** user selects "Reset yearly" as the reset period
- **AND** the first invoice of a new year is generated
- **THEN** system resets the counter to 1 for the new year

#### Scenario: Monthly reset
- **WHEN** user selects "Reset monthly" as the reset period
- **AND** the first invoice of a new month is generated
- **THEN** system resets the counter to 1 for the new month

#### Scenario: Never reset
- **WHEN** user selects "Never reset" as the reset period
- **THEN** the counter increments continuously and never resets

### Requirement: User can set the starting counter value

The system SHALL allow users to set the initial counter value to continue an existing numbering sequence.

#### Scenario: Set starting counter
- **WHEN** user enters a starting counter value (e.g., 150)
- **THEN** the next generated invoice receives number 150
- **AND** subsequent invoices increment from there

#### Scenario: Starting counter validation
- **WHEN** user enters a counter value less than 1
- **THEN** system shows a validation error: counter must be at least 1

### Requirement: Invoice numbers are unique and sequential

The system SHALL guarantee that each invoice number within a tenant is unique and assigned sequentially.

#### Scenario: Sequential assignment
- **WHEN** two invoices are generated
- **THEN** the second invoice receives the next sequential number after the first

#### Scenario: Concurrent generation safety
- **WHEN** two users generate invoices simultaneously
- **THEN** each invoice receives a unique number with no duplicates
- **AND** no counter values are skipped under normal operation

#### Scenario: Uniqueness per tenant
- **WHEN** Tenant A and Tenant B both generate invoices
- **THEN** each tenant has its own independent counter
- **AND** invoice numbers may overlap between tenants (e.g., both can have `RE-2026-0001`)

### Requirement: Number scheme configuration is tenant-scoped

Each tenant SHALL have its own independent number scheme.

#### Scenario: Tenant isolation
- **WHEN** Tenant A configures their number scheme
- **THEN** Tenant B's scheme is unaffected
