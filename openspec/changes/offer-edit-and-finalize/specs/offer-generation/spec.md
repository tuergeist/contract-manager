## MODIFIED Requirements

### Requirement: Create offer from billing schedule event

The system SHALL create an offer from a single billing schedule event row in the revenue forecast tab OR from the contract detail page when the contract status is `draft`.

#### Scenario: Create offer from forecast row
- **WHEN** user clicks "Create Offer" on a billing event row for contract C with billing date D
- **THEN** the system SHALL compute the billing event via `contract.get_billing_schedule(from_date=D, to_date=D)`
- **AND** create an OfferRecord with line items, amounts, and period from that event
- **AND** assign an offer number from the tenant's OfferNumberScheme
- **AND** return the created offer ID

#### Scenario: Create offer from contract detail page
- **WHEN** user clicks "Create Offer" in the contract detail page header
- **AND** the contract status is exactly `draft`
- **THEN** the system SHALL prompt for a `billingDate` (defaulting to the contract's `start_date` or the next computed billing event)
- **AND** invoke the same `OfferService.create_offer(contract_id, billing_date)` code path used by the forecast-row flow
- **AND** redirect the user to the new offer's detail page on success

#### Scenario: Contract-page entry point is gated on draft status
- **WHEN** a contract has status other than `draft` (e.g. `active`, `paused`, `cancelled`, `ended`)
- **THEN** the "Create Offer" button on the contract detail page SHALL NOT be rendered

#### Scenario: Offer creation works for draft and active contracts (forecast entry point)
- **WHEN** a contract has status `draft` or `active`
- **THEN** the "Create Offer" action SHALL be available on its forecast rows

#### Scenario: Tax calculation follows invoice rules
- **WHEN** an offer is created
- **THEN** the system SHALL apply the same domestic/EU/non-EU tax classification as invoices
- **AND** calculate `tax_rate`, `tax_amount`, and `total_gross` accordingly
- **AND** freeze the appropriate VAT sentence

#### Scenario: Minimum term and notice period snapshotted from contract
- **WHEN** an offer is created from a contract
- **THEN** `minimumTermMonths` SHALL be initialized from `contract.min_duration_months` (may be `None`)
- **AND** `noticePeriodMonths` SHALL be initialized from `contract.notice_period_months`

## ADDED Requirements

### Requirement: Offer PDF renders minimum term and notice period conditionally

The system SHALL render minimum-term and notice-period lines into the offer PDF only when their values are set and non-zero.

#### Scenario: Both values set — both rendered
- **WHEN** `minimumTermMonths > 0` and `noticePeriodMonths > 0` on the offer
- **THEN** the PDF SHALL include a "Mindestlaufzeit X Monate ab Vertragsbeginn." line (German) or "Minimum term X months from the contract start date." (English)
- **AND** include a "Kündigungsfrist Y Monate zum Ende der Mindestvertragslaufzeit." line (German) or English equivalent
- **AND** language selection SHALL follow the same `customer.get_effective_invoice_language()` rule as the rest of the document

#### Scenario: Null or zero values — line skipped
- **WHEN** `minimumTermMonths` is `None` or `0`
- **THEN** the minimum-term line SHALL NOT appear in the PDF
- **WHEN** `noticePeriodMonths` is `None` or `0`
- **THEN** the notice-period line SHALL NOT appear in the PDF
