## MODIFIED Requirements

### Requirement: Offer detail page displays full offer data

The system SHALL provide an offer detail page at `/offers/:id` with full offer data, editable fields for draft offers, and lifecycle actions.

#### Scenario: Detail shows metadata
- **WHEN** user navigates to `/offers/123`
- **THEN** the page SHALL display: offer number, offer date, valid until, status, customer (linked), contract (linked), billing period, minimum term, notice period, and a locked-state banner when the offer is `sent` or `finalized`

#### Scenario: Detail shows line items
- **WHEN** user views an offer detail
- **THEN** the page SHALL display the line items from `line_items_snapshot` in a table matching the PDF layout

#### Scenario: Detail shows PDF preview
- **WHEN** the offer has a `pdf_file`
- **THEN** the page SHALL embed the PDF for inline viewing
- **AND** provide a "Download PDF" button

#### Scenario: Detail exposes the two Markdown free-text editors on drafts
- **WHEN** user views a draft offer
- **THEN** the page SHALL render two Markdown textareas labelled "Freitext nach Positionen" (`free_text_after_items`) and "Freitext vor AGB" (`free_text_before_terms`)
- **AND** SHALL show a live Markdown preview next to each editor
- **AND** SHALL save changes via the `updateOffer` mutation and refetch on success

#### Scenario: Detail shows free-text fields as read-only on locked offers
- **WHEN** user views a `sent` or `finalized` offer
- **THEN** the page SHALL render the free-text fields as rendered HTML (read-only)
- **AND** SHALL hide the textarea editors

#### Scenario: Detail exposes editable validity and contract terms on drafts
- **WHEN** user views a draft offer
- **THEN** the page SHALL render editable inputs for `validUntil`, `minimumTermMonths`, `noticePeriodMonths`, and the scoped item set
- **AND** changes SHALL be saved via `updateOffer` with the PDF re-rendering automatically

#### Scenario: Draft lifecycle actions
- **WHEN** user views a draft offer
- **THEN** the page SHALL provide the actions "Send", "Finalize", "Aus Vertrag neu einlesen" (Re-create from contract), and "Delete"
- **AND** the "Aus Vertrag neu einlesen" action SHALL open a confirmation dialog that lists the snapshot fields that will be overwritten and the user-edited fields that will be preserved

#### Scenario: Locked lifecycle actions
- **WHEN** user views a `sent` or `finalized` offer
- **THEN** the page SHALL provide a "Copy to edit" action that calls `cloneOfferToDraft` and redirects to the new draft
- **AND** SHALL NOT provide Send, Finalize, Re-create, or Delete actions

#### Scenario: Offer not found
- **WHEN** user navigates to `/offers/999` and no offer exists
- **THEN** the page SHALL display an error message

## ADDED Requirements

### Requirement: Contract detail page exposes a Create Offer entry point

The system SHALL render a "Create Offer" button on the contract detail page header, left of the existing "Add Todo" button, visible only when the contract status is exactly `draft`.

#### Scenario: Button visibility tied to draft status
- **WHEN** the contract status is `draft`
- **THEN** the contract detail page header SHALL include a "Create Offer" button to the left of "Add Todo"
- **WHEN** the contract status is anything other than `draft`
- **THEN** the button SHALL NOT be rendered

#### Scenario: Button opens billing-date prompt
- **WHEN** user clicks the "Create Offer" button
- **THEN** the page SHALL show a prompt asking for the billing date (defaulting to the contract's next computed billing event or its start date)
- **AND** call `createOffer(contractId, billingDate)` on confirmation
- **AND** redirect to the new offer's detail page on success
