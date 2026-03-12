## MODIFIED Requirements

### Requirement: OfferRecord persists offer data with frozen snapshots

The system SHALL store offers as `OfferRecord` instances with frozen line items, company data, and customer data captured at creation time. Offers MAY be scoped to specific contract items instead of all items.

#### Scenario: Offer created from billing event
- **WHEN** an offer is created from a billing schedule event
- **THEN** the system SHALL create an OfferRecord with:
  - `offer_number` assigned from OfferNumberScheme
  - `contract` and `customer` FK links
  - `offer_date` set to today
  - `valid_until` set to 30 days from today (default)
  - `billing_date`, `period_start`, `period_end` from the billing event
  - `total_net`, `tax_rate`, `tax_amount`, `total_gross` calculated
  - `line_items_snapshot` frozen from billing event items
  - `company_data_snapshot` frozen from tenant's CompanyLegalData
  - `status` set to `draft`

#### Scenario: Offer snapshots are immutable
- **WHEN** the contract's prices or company data change after offer creation
- **THEN** the offer's `line_items_snapshot` and `company_data_snapshot` SHALL remain unchanged

#### Scenario: Offer scoped to specific items
- **WHEN** an offer is created with an explicit list of contract item IDs
- **THEN** the `line_items_snapshot` SHALL contain only those items
- **AND** `total_net`, `tax_amount`, `total_gross` SHALL be calculated from only those items
- **AND** the `scoped_item_ids` field SHALL store the list of item IDs for reference

#### Scenario: Offer without item scope includes all items
- **WHEN** an offer is created without specifying item IDs
- **THEN** the system SHALL include all contract items in the snapshot (existing behavior)
