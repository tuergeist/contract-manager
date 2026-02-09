## ADDED Requirements

### Requirement: User can configure company legal data

The system SHALL provide a settings form for entering all company data required by German HGB/UStG §14 for GmbH invoices.

#### Scenario: Enter mandatory company identification
- **WHEN** user navigates to `/settings/company-data`
- **THEN** system displays a form with fields for:
  - Company name (with legal form, e.g., "Muster GmbH")
  - Street address
  - ZIP code
  - City
  - Country

#### Scenario: Enter tax identification
- **WHEN** user fills in tax identification fields
- **THEN** system accepts:
  - Tax number (Steuernummer) — optional if VAT ID is provided
  - VAT ID (USt-IdNr.) — optional if tax number is provided
- **AND** at least one of tax number or VAT ID MUST be provided

#### Scenario: Enter commercial register data
- **WHEN** user fills in commercial register fields
- **THEN** system accepts:
  - Register court (Amtsgericht), e.g., "Amtsgericht München"
  - Register number (HRB), e.g., "HRB 12345"
- **AND** both fields are required for GmbH

#### Scenario: Enter managing directors
- **WHEN** user fills in the managing directors field
- **THEN** system accepts one or more names (Geschäftsführer)
- **AND** at least one managing director is required

#### Scenario: Enter bank details
- **WHEN** user fills in bank detail fields
- **THEN** system accepts:
  - Bank name
  - IBAN
  - BIC
- **AND** all three fields are optional but recommended

#### Scenario: Enter contact information
- **WHEN** user fills in contact fields
- **THEN** system accepts:
  - Phone number (optional)
  - Email address (optional)
  - Website URL (optional)

#### Scenario: Enter share capital
- **WHEN** user fills in the share capital field
- **THEN** system accepts the Stammkapital amount (optional)

### Requirement: Company legal data is validated on save

The system SHALL validate company legal data when the user saves the form.

#### Scenario: Successful save with all required fields
- **WHEN** user has filled in company name, address, at least one tax ID, register court, register number, and at least one managing director
- **AND** clicks save
- **THEN** system stores the data and shows a success message

#### Scenario: Save rejected with missing required fields
- **WHEN** user attempts to save without required fields (e.g., no company name)
- **THEN** system shows validation errors highlighting the missing fields
- **AND** data is not saved

#### Scenario: Tax ID cross-validation
- **WHEN** user provides neither tax number nor VAT ID
- **AND** attempts to save
- **THEN** system shows error: "At least one of Tax Number or VAT ID is required"

#### Scenario: IBAN format validation
- **WHEN** user enters an IBAN
- **THEN** system validates the IBAN format (starts with 2-letter country code, followed by 2 check digits and up to 30 alphanumeric characters)

### Requirement: Default tax rate configuration

The system SHALL allow users to configure a default tax rate (USt-Satz) for invoice generation.

#### Scenario: Set default tax rate
- **WHEN** user enters a default tax rate (e.g., 19.00)
- **THEN** system stores the rate
- **AND** all generated invoices use this rate unless overridden

#### Scenario: Default tax rate value
- **WHEN** no tax rate has been configured
- **THEN** system defaults to 19.00% (German standard rate)

### Requirement: Invoices include all legally required information

Generated invoices SHALL include all fields required by UStG §14 Abs. 4.

#### Scenario: Invoice contains supplier identification
- **WHEN** an invoice PDF is generated
- **THEN** it SHALL display the company's full legal name, complete address, and tax number or VAT ID

#### Scenario: Invoice contains recipient identification
- **WHEN** an invoice PDF is generated
- **THEN** it SHALL display the customer's name and address

#### Scenario: Invoice contains unique sequential number
- **WHEN** an invoice PDF is generated
- **THEN** it SHALL display the assigned invoice number prominently

#### Scenario: Invoice contains date information
- **WHEN** an invoice PDF is generated
- **THEN** it SHALL display:
  - Invoice date (Rechnungsdatum)
  - Delivery/service date or period (Leistungsdatum / Leistungszeitraum)

#### Scenario: Invoice contains itemized amounts with tax
- **WHEN** an invoice PDF is generated
- **THEN** each line item SHALL show net amount
- **AND** the invoice SHALL show: total net amount (Nettobetrag), applicable tax rate, tax amount (Steuerbetrag), and gross total (Bruttobetrag)

#### Scenario: Invoice contains GmbH-specific footer
- **WHEN** an invoice PDF is generated
- **THEN** it SHALL include a footer section with:
  - Commercial register court and number (e.g., "Amtsgericht München, HRB 12345")
  - Managing director(s) names
  - Bank details (if configured)
  - Share capital (if configured)

### Requirement: System prevents invoice generation without legal data

The system SHALL prevent generating finalized invoices when required legal data is missing.

#### Scenario: Block generation without legal data
- **WHEN** user attempts to generate/finalize invoices
- **AND** company legal data has not been configured
- **THEN** system displays an error: "Company legal data must be configured before generating invoices"
- **AND** provides a link to `/settings/company-data`

#### Scenario: Block generation with incomplete legal data
- **WHEN** user attempts to generate/finalize invoices
- **AND** required legal fields are missing (e.g., no tax ID)
- **THEN** system displays an error listing the missing fields

### Requirement: Company legal data is tenant-scoped

Each tenant SHALL have its own independent company legal data.

#### Scenario: Tenant isolation
- **WHEN** Tenant A configures their company data
- **THEN** Tenant B's data is unaffected
- **AND** each tenant's invoices display their own company information
