## ADDED Requirements

### Requirement: System generates ZUGFeRD EN 16931 XML from invoice data

The system SHALL generate valid UN/CEFACT Cross-Industry Invoice (CII) XML conforming to the ZUGFeRD EN 16931 (Comfort) profile from existing invoice records.

#### Scenario: Generate XML for a finalized invoice record
- **WHEN** a finalized `InvoiceRecord` is provided to the ZUGFeRD service
- **THEN** system generates CII XML containing:
  - Exchange document context with EN 16931 profile identifier (`urn:cen.eu:en16931:2017`)
  - Invoice number from `InvoiceRecord.invoice_number`
  - Invoice type code (380 = Commercial Invoice)
  - Invoice date from `InvoiceRecord.billing_date`
  - Invoice currency from `Tenant.currency`

#### Scenario: XML contains seller information
- **WHEN** ZUGFeRD XML is generated
- **THEN** the SellerTradeParty section SHALL include:
  - Company name from `CompanyLegalData.company_name`
  - Full postal address (street, postcode, city, country code)
  - VAT ID (`CompanyLegalData.vat_id`) as tax registration with scheme ID "VA"
  - Tax number (`CompanyLegalData.tax_number`) as tax registration with scheme ID "FC" (if no VAT ID)

#### Scenario: XML contains buyer information
- **WHEN** ZUGFeRD XML is generated
- **THEN** the BuyerTradeParty section SHALL include:
  - Customer name from `InvoiceRecord.customer_name` or `Customer.name`
  - Postal address from `Customer.address` JSON (street, zip, city, country)
  - Buyer VAT ID from `Customer.address.vat_id` if available (optional)

#### Scenario: XML contains line items
- **WHEN** ZUGFeRD XML is generated for an invoice with N line items
- **THEN** the XML SHALL contain N `IncludedSupplyChainTradeLineItem` elements
- **AND** each line item SHALL include:
  - Line item number (sequential, starting at 1)
  - Product name from `line_items_snapshot[].product_name`
  - Quantity with unit code "C62" (one/piece)
  - Net unit price from `line_items_snapshot[].unit_price`
  - Line total (net) from `line_items_snapshot[].amount`
  - VAT category code "S" (standard rate) with the invoice tax rate

#### Scenario: XML contains tax summary
- **WHEN** ZUGFeRD XML is generated
- **THEN** the ApplicableHeaderTradeSettlement SHALL include:
  - One `ApplicableTradeTax` entry with category code "S"
  - Tax rate from `InvoiceRecord.tax_rate`
  - Tax basis amount (net total) from `InvoiceRecord.total_net`
  - Tax amount from `InvoiceRecord.tax_amount`

#### Scenario: XML contains monetary totals
- **WHEN** ZUGFeRD XML is generated
- **THEN** the SpecifiedTradeSettlementHeaderMonetarySummation SHALL include:
  - Line total amount = sum of line items
  - Tax basis total = `InvoiceRecord.total_net`
  - Tax total = `InvoiceRecord.tax_amount` (with currency attribute)
  - Grand total = `InvoiceRecord.total_gross`
  - Due payable amount = `InvoiceRecord.total_gross`

#### Scenario: XML contains payment information
- **WHEN** ZUGFeRD XML is generated
- **AND** `CompanyLegalData` has bank details configured (IBAN, BIC)
- **THEN** the SpecifiedTradePaymentTerms SHALL include payment means type code 58 (SEPA credit transfer)
- **AND** the PayeePartyCreditorFinancialAccount SHALL include the IBAN
- **AND** the PayeeSpecifiedCreditorFinancialInstitution SHALL include the BIC

#### Scenario: XML contains billing period
- **WHEN** ZUGFeRD XML is generated
- **THEN** the BillingSpecifiedPeriod SHALL include:
  - Start date from `InvoiceRecord.period_start`
  - End date from `InvoiceRecord.period_end`

#### Scenario: XML contains invoice note
- **WHEN** ZUGFeRD XML is generated
- **AND** `InvoiceRecord.invoice_text` is not empty
- **THEN** the XML SHALL include an IncludedNote element with the invoice text

### Requirement: Generated XML passes XSD validation

The system SHALL validate generated XML against the UN/CEFACT CII XSD schemas.

#### Scenario: Valid XML passes validation
- **WHEN** XML is generated for a complete invoice record
- **THEN** XSD validation SHALL pass without errors

#### Scenario: Validation failure is logged but non-blocking
- **WHEN** XML validation fails (e.g., due to missing optional data)
- **THEN** system SHALL log the validation errors as warnings
- **AND** SHALL still produce the XML (best-effort)
- **AND** SHALL include a `validation_warnings` field in the service response

### Requirement: XML generation works from both InvoiceRecord and InvoiceData

The system SHALL support generating ZUGFeRD XML from both persisted `InvoiceRecord` objects and on-demand `InvoiceData` dataclasses.

#### Scenario: Generate from InvoiceRecord (persisted)
- **WHEN** a finalized `InvoiceRecord` is provided
- **THEN** system uses `company_data_snapshot` and `line_items_snapshot` for XML generation
- **AND** uses the frozen data (not current company/contract data)

#### Scenario: Generate from InvoiceData (preview/on-demand)
- **WHEN** an `InvoiceData` dataclass is provided (not yet persisted)
- **THEN** system fetches current `CompanyLegalData` for seller info
- **AND** uses the `InvoiceData` line items and customer info
- **AND** uses "PREVIEW" as invoice number placeholder

### Requirement: XML generation is tenant-scoped

#### Scenario: Tenant isolation
- **WHEN** ZUGFeRD XML is generated for Tenant A
- **THEN** seller information comes from Tenant A's `CompanyLegalData`
- **AND** no data from other tenants is included
