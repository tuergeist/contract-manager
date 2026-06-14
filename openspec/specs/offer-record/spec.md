## Purpose

Persistent OfferRecord model, sequential offer numbering, status lifecycle, and the GraphQL surface for offers. Defines the editable surface for drafts vs the immutable snapshot fields rewritten by re-create.
## Requirements
### Requirement: OfferRecord persists offer data with frozen snapshots

The system SHALL store offers as `OfferRecord` instances with frozen contract-derived snapshots and a user-editable surface. Offers MAY be scoped to specific contract items instead of all items.

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
  - `minimum_term_months` initialized from `contract.min_duration_months`
  - `notice_period_months` initialized from `contract.notice_period_months`
  - `free_text_after_items` and `free_text_before_terms` initialized to empty strings
  - `cloned_from` set to `None`
  - `status` set to `draft`

#### Scenario: Contract-derived snapshots are overwritten by re-create only
- **WHEN** the contract's prices or company data change after offer creation
- **THEN** the offer's `line_items_snapshot`, `company_data_snapshot`, `customer_name`, `contract_name`, `period_start`, `period_end`, `total_net`, `tax_rate`, `tax_amount`, `total_gross`, and `vat_sentence` SHALL remain unchanged
- **AND** SHALL only be replaced when the `recreateOfferFromContract` mutation is called on a draft offer

#### Scenario: User-editable fields are preserved across re-create
- **WHEN** `recreateOfferFromContract` runs
- **THEN** the user-editable fields `free_text_after_items`, `free_text_before_terms`, `valid_until`, `minimum_term_months`, `notice_period_months`, and the `scoped_item_ids` setting SHALL be preserved

#### Scenario: Offer scoped to specific items
- **WHEN** an offer is created with an explicit list of contract item IDs
- **THEN** the `line_items_snapshot` SHALL contain only those items
- **AND** `total_net`, `tax_amount`, `total_gross` SHALL be calculated from only those items
- **AND** the `scoped_item_ids` field SHALL store the list of item IDs for reference

#### Scenario: Offer without item scope includes all items
- **WHEN** an offer is created without specifying item IDs
- **THEN** the system SHALL store `scoped_item_ids = None` (implicit "all items")
- **AND** include all contract items in the snapshot

### Requirement: Offer status lifecycle

The system SHALL enforce the following status transitions for offers.

#### Scenario: Valid status transitions
- **GIVEN** an offer in `draft` status
- **THEN** it MAY transition to `sent` (system-driven, on successful email send) or `finalized` (user-driven, via Finalize action)
- **GIVEN** an offer in `sent` or `finalized` status
- **THEN** no further transitions SHALL be permitted

#### Scenario: Expired offers
- **WHEN** an offer's `valid_until` date is in the past and status is `draft`, `sent`, or `finalized`
- **THEN** the offer list SHALL display it with an expired visual indicator
- **AND** the offer SHALL otherwise behave according to its actual status (draft remains editable, locked stays locked)

### Requirement: OfferNumberScheme provides configurable numbering

The system SHALL provide an `OfferNumberScheme` model with the same structure as `InvoiceNumberScheme`.

#### Scenario: Default numbering pattern
- **WHEN** no OfferNumberScheme exists for a tenant
- **THEN** the system SHALL create one with default pattern `{YYYY}-{NNNN}` and yearly reset

#### Scenario: Configurable pattern
- **WHEN** a user configures the offer number pattern in settings
- **THEN** the system SHALL support the same placeholders as invoice numbering: `{YYYY}`, `{YY}`, `{MM}`, `{NNN}`, `{NNNN}`, `{NNNNN}`

#### Scenario: Unique offer numbers per tenant
- **WHEN** an offer number is assigned
- **THEN** it SHALL be unique within the tenant (enforced by database constraint)

### Requirement: GraphQL API for offers

The system SHALL expose offer CRUD operations via GraphQL.

#### Scenario: Query single offer
- **WHEN** user queries `offer(id: Int!)`
- **THEN** the system SHALL return the full OfferRecordType (including the new editable and snapshot fields) if it belongs to the user's tenant, or null otherwise

#### Scenario: Query offer list
- **WHEN** user queries `offers` with optional filters (search, status, dateFrom, dateTo)
- **THEN** the system SHALL return a paginated list of offers for the user's tenant

#### Scenario: Update offer is restricted to the editable surface
- **WHEN** user calls `updateOffer(id, input)` on a draft offer
- **THEN** the system SHALL accept only `freeTextAfterItems`, `freeTextBeforeTerms`, `validUntil`, `minimumTermMonths`, `noticePeriodMonths`, `scopedItemIds`
- **AND** reject any other field with a validation error

#### Scenario: Re-create from contract mutation
- **WHEN** user calls `recreateOfferFromContract(id)` on a draft offer
- **THEN** the system SHALL re-snapshot contract-derived fields while preserving user-edited fields and the existing `offer_number`

#### Scenario: Finalize mutation
- **WHEN** user calls `finalizeOffer(id)` on a draft offer with the `offers.finalize` permission
- **THEN** the system SHALL transition the offer to `finalized` and attach the PDF to the parent contract

#### Scenario: Clone-to-edit mutation
- **WHEN** user calls `cloneOfferToDraft(id)` on a locked offer
- **THEN** the system SHALL create a new draft offer with a fresh `offer_number` and `cloned_from` set to the source

#### Scenario: Delete draft offer
- **WHEN** user calls `deleteOffer(id)` on a draft offer
- **THEN** the system SHALL delete the offer record
- **WHEN** user calls `deleteOffer(id)` on a non-draft offer
- **THEN** the system SHALL return an error

### Requirement: OfferRecord exposes editable and identity fields

The system SHALL extend `OfferRecord` with the new fields needed to support draft editing, free-text rendering, and clone audit.

#### Scenario: New fields exist with safe defaults
- **WHEN** a new `OfferRecord` is created
- **THEN** it SHALL have:
  - `free_text_after_items: TextField` defaulting to `""` (empty string)
  - `free_text_before_terms: TextField` defaulting to `""`
  - `minimum_term_months: PositiveIntegerField` defaulting to `None`
  - `notice_period_months: PositiveIntegerField` defaulting to `None`
  - `cloned_from: ForeignKey('self')` defaulting to `None`, `on_delete=SET_NULL`

#### Scenario: Cloned offers reference their source
- **WHEN** an offer is created via `cloneOfferToDraft`
- **THEN** `cloned_from` SHALL point to the source OfferRecord

#### Scenario: Existing offers are unaffected by the migration
- **WHEN** the migration adding these fields is applied
- **THEN** existing `OfferRecord` rows SHALL have `free_text_*` set to empty string, `minimum_term_months` and `notice_period_months` set to `None`, and `cloned_from` set to `None`
- **AND** no retroactive snapshot updates SHALL occur

<!--
  Notes on removed behavior (handled by the MODIFIED requirements above):

  - The previous `updateOffer(id, validUntil, notes)` mutation signature is
    replaced by `updateOffer(id, input: UpdateOfferInput!)` covering the
    full editable surface. The legacy `notes` field stays on the model for
    backwards-compatible reads but is no longer rendered.
  - The previous free-form `updateOfferStatus(id, status)` mutation is
    deprecated. The lifecycle is now `draft → sent | finalized` only;
    `sent` is system-driven inside the email-send task, `finalized` is the
    user-driven Finalize action. The old `accepted / rejected / cancelled /
    expired` values stay readable in existing rows but no new transition
    lands there.

  These are captured in the MODIFIED "GraphQL API for offers" and
  "Offer status lifecycle" requirements above. No formal REMOVED block
  is needed because the legacy behavior was scenarios inside existing
  requirements, not requirements of their own.
-->

