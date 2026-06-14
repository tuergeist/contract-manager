# offer-finalize Specification

## Purpose
TBD - created by archiving change offer-edit-and-finalize. Update Purpose after archive.
## Requirements
### Requirement: Offer lifecycle has two terminal locked states

The system SHALL support exactly two transitions out of `draft`: `draft → sent` (system-driven on successful email send) and `draft → finalized` (user-driven via the Finalize action). Both `sent` and `finalized` SHALL be terminal locked states; no further state transitions are permitted.

#### Scenario: Draft can transition to sent
- **WHEN** an email send for a draft offer succeeds and `emailSentAt` is recorded
- **THEN** the system SHALL set status to `sent`
- **AND** trigger the contract-attachment copy

#### Scenario: Draft can transition to finalized
- **WHEN** user calls `finalizeOffer(id)` on a draft offer
- **THEN** the system SHALL set status to `finalized`
- **AND** trigger the contract-attachment copy

#### Scenario: Terminal states are locked
- **WHEN** an offer is in `sent` or `finalized`
- **THEN** any subsequent call to `updateOffer`, `recreateOfferFromContract`, or `deleteOffer` SHALL be rejected with `OfferLockedError`

### Requirement: Finalize is idempotent and race-safe

The system SHALL ensure that concurrent finalize-and-send calls on the same draft offer result in exactly one terminal state.

#### Scenario: Finalize twice is a no-op
- **WHEN** user calls `finalizeOffer(id)` on an already-finalized offer
- **THEN** the mutation SHALL return success=true
- **AND** the OfferRecord SHALL be unchanged

#### Scenario: Finalize rejected on sent offer
- **WHEN** user calls `finalizeOffer(id)` on a `sent` offer
- **THEN** the mutation SHALL return success=false with `OfferLockedError`

#### Scenario: Concurrent finalize and send
- **WHEN** `finalizeOffer` and the email-send task hit the same draft offer in parallel
- **THEN** both code paths SHALL acquire a row-level lock (`SELECT ... FOR UPDATE`) on the OfferRecord
- **AND** exactly one SHALL succeed in moving the offer out of `draft`
- **AND** the other SHALL observe the now-locked state and return its corresponding error

### Requirement: Send failure does not lock the offer

The system SHALL only transition an offer to `sent` after the email delivery has completed successfully and `emailSentAt` has been persisted.

#### Scenario: SMTP failure leaves draft intact
- **WHEN** the email-send task raises an SMTP or delivery error
- **THEN** the OfferRecord status SHALL remain `draft`
- **AND** `emailSentAt` SHALL remain unset
- **AND** the offer SHALL stay fully editable for the user to retry

#### Scenario: Successful send locks
- **WHEN** the email-send task records `emailSentAt`
- **THEN** the status SHALL transition to `sent` in the same transaction
- **AND** the contract-attachment copy SHALL run as the last step

### Requirement: Locked offers attach their PDF to the contract

The system SHALL copy the offer's PDF into a new `ContractAttachment` row on the parent contract every time an offer transitions from `draft` to a locked state.

#### Scenario: Attachment created on first lock
- **WHEN** an offer transitions from `draft` to `sent` or `finalized` and no `ContractAttachment` for this offer exists yet
- **THEN** the system SHALL create a `ContractAttachment` row with:
  - `contract` set to the offer's parent contract
  - `category` set to `offer`
  - `source_offer` set to the OfferRecord
  - `description` set to "Angebot {offerNumber}" in the tenant's default language ("Offer {offerNumber}" in English)
  - `file` containing a fresh copy of the bytes from `OfferRecord.pdf_file`
- **AND** the attachment SHALL appear in `Contract.attachments` immediately

#### Scenario: Attachment copy is idempotent
- **WHEN** the attachment copy runs and a `ContractAttachment` with `source_offer` matching this OfferRecord already exists
- **THEN** the system SHALL NOT create a duplicate row
- **AND** SHALL return the existing attachment

#### Scenario: Multiple finalized offers produce multiple attachments
- **WHEN** several offers on the same contract are independently sent or finalized
- **THEN** each one SHALL produce its own `ContractAttachment` row
- **AND** all SHALL be visible in the contract's attachments list

#### Scenario: Attachment survives offer deletion
- **WHEN** the source OfferRecord is deleted
- **THEN** `ContractAttachment.source_offer` SHALL be set to `NULL`
- **AND** the attachment row SHALL remain in the contract's attachments list

### Requirement: Copy-to-edit clones a locked offer into a new draft

The system SHALL provide a `cloneOfferToDraft(id)` mutation that creates a new draft offer from a locked source, allowing the user to iterate without modifying history.

#### Scenario: Clone creates a new draft from a locked offer
- **WHEN** user calls `cloneOfferToDraft(id)` on a `sent` or `finalized` OfferRecord
- **THEN** the system SHALL create a new `OfferRecord` with:
  - A new `offerNumber` from the tenant's `OfferNumberScheme`
  - `status` set to `draft`
  - `cloned_from` FK pointing to the source OfferRecord
  - `lineItemsSnapshot`, `companyDataSnapshot`, `customerName`, `contractName`, `periodStart`, `periodEnd`, `totalNet`, `taxRate`, `taxAmount`, `totalGross`, `vatSentence`, `scopedItemIds`, `freeTextAfterItems`, `freeTextBeforeTerms`, `minimumTermMonths`, `noticePeriodMonths`, `validUntil` copied from the source
  - `offerDate` set to today
- **AND** generate a fresh PDF for the new draft
- **AND** return the new offer

#### Scenario: Clone does not re-read the contract
- **WHEN** `cloneOfferToDraft` runs
- **THEN** the system SHALL NOT re-fetch billing events from the contract
- **AND** the new draft SHALL show the same line items and amounts as the source

#### Scenario: Clone rejected on draft source
- **WHEN** user calls `cloneOfferToDraft(id)` on a draft offer
- **THEN** the mutation SHALL return success=false with a clear error
- **AND** no new OfferRecord SHALL be created

### Requirement: Finalize is a separately granted permission

The system SHALL gate the `finalizeOffer` mutation behind a dedicated `offers.finalize` permission, separate from `offers.write`.

#### Scenario: User without finalize permission is rejected
- **WHEN** a user with `offers.write` but without `offers.finalize` calls `finalizeOffer`
- **THEN** the mutation SHALL return a permission-denied error
- **AND** the OfferRecord SHALL remain `draft`

#### Scenario: Admin role grants finalize by default
- **WHEN** the Admin role is provisioned for a new tenant
- **THEN** it SHALL include `offers.finalize` in its permissions

