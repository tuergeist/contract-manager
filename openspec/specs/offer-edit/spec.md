# offer-edit Specification

## Purpose
TBD - created by archiving change offer-edit-and-finalize. Update Purpose after archive.
## Requirements
### Requirement: Draft offers are editable through a dedicated mutation

The system SHALL allow modifications to an `OfferRecord` while its status is `draft`, and SHALL reject any modification attempt on a non-draft offer at the service layer.

#### Scenario: Update draft offer fields
- **WHEN** user calls `updateOffer(id, input)` with any subset of `freeTextAfterItems`, `freeTextBeforeTerms`, `validUntil`, `minimumTermMonths`, `noticePeriodMonths`, `scopedItemIds`
- **AND** the offer status is `draft`
- **THEN** the system SHALL apply the supplied fields atomically inside a `select_for_update` transaction
- **AND** persist the updated record
- **AND** regenerate the offer PDF synchronously before returning success

#### Scenario: Update rejected for locked offer
- **WHEN** user calls `updateOffer(id, input)` on an offer with status `sent` or `finalized`
- **THEN** the mutation SHALL return success=false with an `OfferLockedError` payload
- **AND** the OfferRecord SHALL NOT be modified

#### Scenario: Update rejects fields outside the editable surface
- **WHEN** an `updateOffer` request includes a field that is NOT in {`freeTextAfterItems`, `freeTextBeforeTerms`, `validUntil`, `minimumTermMonths`, `noticePeriodMonths`, `scopedItemIds`}
- **THEN** the system SHALL reject the request with a validation error before any write

#### Scenario: Empty Markdown is rendered as no block
- **WHEN** `freeTextAfterItems` or `freeTextBeforeTerms` is empty or whitespace-only
- **THEN** the regenerated PDF SHALL omit that block entirely

#### Scenario: Scoped item IDs validation
- **WHEN** `scopedItemIds` is supplied as an empty list `[]`
- **THEN** the mutation SHALL return a validation error
- **WHEN** `scopedItemIds` is supplied as `null`
- **THEN** the system SHALL store `None` (implicit "all items") and recompute line items from the full contract item set

### Requirement: Re-create from contract refreshes contract-derived snapshots only

The system SHALL provide a `recreateOfferFromContract` mutation that re-snapshots the contract's current billing data into an existing draft offer while preserving user-edited fields.

#### Scenario: Re-create overwrites contract-derived fields
- **WHEN** user calls `recreateOfferFromContract(id)` on a draft offer
- **THEN** the system SHALL re-fetch the contract's billing event for the offer's `billingDate`
- **AND** overwrite `lineItemsSnapshot`, `companyDataSnapshot`, `customerName`, `contractName`, `periodStart`, `periodEnd`, `totalNet`, `taxRate`, `taxAmount`, `totalGross`, and `vatSentence`
- **AND** preserve `freeTextAfterItems`, `freeTextBeforeTerms`, `validUntil`, `minimumTermMonths`, `noticePeriodMonths`
- **AND** preserve the existing `offerNumber`
- **AND** regenerate the PDF synchronously

#### Scenario: Re-create respects implicit vs explicit scope
- **WHEN** the offer's `scopedItemIds` is `None` (implicit)
- **THEN** re-create SHALL leave `scopedItemIds` as `None` and recompute line items from the contract's full current item set
- **WHEN** the offer's `scopedItemIds` is an explicit list
- **THEN** re-create SHALL preserve the explicit list and recompute line items for only those IDs (ignoring item IDs that no longer exist on the contract)

#### Scenario: Re-create rejected on locked offer
- **WHEN** user calls `recreateOfferFromContract(id)` on an offer with status `sent` or `finalized`
- **THEN** the mutation SHALL return success=false with an `OfferLockedError`

#### Scenario: Re-create fails when no billing event matches
- **WHEN** the contract has no billing event on the offer's `billingDate` after contract changes
- **THEN** the mutation SHALL return success=false with a clear error
- **AND** the OfferRecord SHALL NOT be modified

### Requirement: Markdown free-text fields are rendered into the PDF

The system SHALL render the two Markdown free-text fields at fixed positions in the offer PDF, sanitizing the rendered HTML to a safe allowlist.

#### Scenario: free_text_after_items renders below line items
- **WHEN** an offer with non-empty `freeTextAfterItems` is rendered
- **THEN** the PDF SHALL display the rendered Markdown directly below the line-item table
- **AND** above any tax summary block

#### Scenario: free_text_before_terms renders above T&C / VAT block
- **WHEN** an offer with non-empty `freeTextBeforeTerms` is rendered
- **THEN** the PDF SHALL display the rendered Markdown directly above the VAT sentence and any T&C block

#### Scenario: Markdown is sanitized
- **WHEN** Markdown is rendered for the PDF
- **THEN** the HTML output SHALL be filtered through an allowlist of `p, br, em, strong, ul, ol, li, code, blockquote, h3, h4`
- **AND** SHALL NOT include `script`, `style`, inline `style=` attributes, `a`, or `img` tags

