## ADDED Requirements

### Requirement: Create offer from billing schedule event

The system SHALL create an offer from a single billing schedule event row in the revenue forecast tab.

#### Scenario: Create offer from forecast row
- **WHEN** user clicks "Create Offer" on a billing event row for contract C with billing date D
- **THEN** the system SHALL compute the billing event via `contract.get_billing_schedule(from_date=D, to_date=D)`
- **AND** create an OfferRecord with line items, amounts, and period from that event
- **AND** assign an offer number from the tenant's OfferNumberScheme
- **AND** return the created offer ID

#### Scenario: Offer creation works for draft and active contracts
- **WHEN** a contract has status `draft` or `active`
- **THEN** the "Create Offer" action SHALL be available on its forecast rows

#### Scenario: Tax calculation follows invoice rules
- **WHEN** an offer is created
- **THEN** the system SHALL apply the same domestic/EU/non-EU tax classification as invoices
- **AND** calculate `tax_rate`, `tax_amount`, and `total_gross` accordingly
- **AND** freeze the appropriate VAT sentence

### Requirement: Offer PDF generation

The system SHALL generate a PDF for each offer using a dedicated template.

#### Scenario: PDF contains offer metadata
- **WHEN** an offer PDF is generated
- **THEN** it SHALL display:
  - Company logo and legal data (from snapshot)
  - Customer address
  - Offer number and offer date
  - "Valid until" date
  - Billing/service period
  - Line items table (pos, description, qty, unit price, amount)
  - Net total, tax breakdown (if domestic), gross total
  - VAT sentence (if foreign customer)
  - Notes/conditions (if set)

#### Scenario: PDF title reflects document type
- **WHEN** an offer PDF is rendered in German
- **THEN** the title SHALL be "Angebot"
- **WHEN** rendered in English
- **THEN** the title SHALL be "Offer"

#### Scenario: PDF uses customer's invoice language
- **WHEN** the customer has `invoice_language` set
- **THEN** the offer PDF SHALL use that language
- **WHEN** not set
- **THEN** it SHALL fall back to the tenant default language

#### Scenario: PDF generated on offer creation
- **WHEN** an offer is created
- **THEN** the PDF SHALL be generated and stored in `pdf_file`
