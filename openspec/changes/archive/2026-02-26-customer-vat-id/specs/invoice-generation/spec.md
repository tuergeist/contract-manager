## MODIFIED Requirements

### Requirement: Invoice includes complete billing details

Each generated invoice SHALL include all information needed for customer billing and accounting, including contract metadata such as invoice text, PO number, order confirmation number, and customer VAT ID when available.

#### Scenario: Invoice contains required fields
- **WHEN** an invoice is generated
- **THEN** it SHALL include: customer name, customer address, contract name, billing date, line items with product/description/quantity/unit price/total, invoice total, and billing period covered

#### Scenario: Invoice respects item-level billing dates
- **WHEN** a contract item has a custom billing_start_date or billing_end_date
- **THEN** the item is only included in invoices within its billing period
- **AND** items outside their billing period are excluded

#### Scenario: Invoice handles prorated items
- **WHEN** a contract item has align_to_contract_at set
- **THEN** the first billing period is prorated
- **AND** the prorated amount and factor are included in the line item

#### Scenario: Invoice PDF shows PO number when present
- **WHEN** the contract has a PO number set
- **THEN** the invoice PDF metadata section SHALL display the PO number with label "Bestellnummer" (DE) or "PO Number" (EN)

#### Scenario: Invoice PDF shows order confirmation number when present
- **WHEN** the contract has an order confirmation number set
- **THEN** the invoice PDF metadata section SHALL display it with label "Auftragsbestätigung" (DE) or "Order Confirmation" (EN)

#### Scenario: Invoice PDF shows invoice text when present
- **WHEN** the contract has invoice_text set
- **THEN** the invoice PDF SHALL render the text below the totals section, before the footer

#### Scenario: Invoice PDF omits empty metadata fields
- **WHEN** the contract has no PO number, no order confirmation number, or no invoice text
- **THEN** the corresponding sections SHALL not appear on the PDF

#### Scenario: Invoice preview includes metadata fields
- **WHEN** a preview PDF is generated
- **THEN** it SHALL include sample PO number, order confirmation number, and invoice text to demonstrate the layout

#### Scenario: Invoice PDF shows customer VAT ID when present
- **WHEN** an invoice is generated for a customer with `vat_id` set
- **THEN** the PDF SHALL display the VAT ID below the customer address block with label "USt-IdNr." (DE) or "VAT ID" (EN)

#### Scenario: Invoice PDF omits VAT ID line when empty
- **WHEN** an invoice is generated for a customer without a VAT ID
- **THEN** no VAT ID line SHALL appear in the recipient address block
