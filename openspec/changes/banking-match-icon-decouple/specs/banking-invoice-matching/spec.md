## ADDED Requirements

### Requirement: Match status pill in transaction listings
The system SHALL display match status as an explicit text pill ("Offen" / "Teilweise" / "Bezahlt") in the banking transaction list and counterparty detail tables, separate from the action icon.

#### Scenario: Open transaction
- **WHEN** a transaction has zero matches
- **THEN** the row shows a grey "Offen" pill

#### Scenario: Partially matched transaction
- **WHEN** a transaction has matches that cover less than 100% of the amount
- **THEN** the row shows a yellow "Teilweise" pill with count, e.g. "Teilweise (1/3)"

#### Scenario: Fully matched transaction
- **WHEN** a transaction has matches summing to the full amount (within ±0.01)
- **THEN** the row shows a green "Bezahlt" pill (with count if more than 1 match)

#### Scenario: Action icon decoupled from status
- **WHEN** the user clicks the action icon
- **THEN** the match sheet always opens, regardless of match status; tooltip text reflects current state ("Match bearbeiten" vs "Zuordnen")

#### Scenario: Quick-link only for single match
- **WHEN** a transaction has exactly one matched invoice
- **THEN** a FileText quick-link is rendered next to the pill, routing to the correct invoice type page (incoming / imported / generated)

#### Scenario: No quick-link for multi-match
- **WHEN** a transaction has more than one matched invoice
- **THEN** the FileText quick-link is hidden; the user opens the match sheet to see the list

### Requirement: Match summary exposed in listing queries
The system SHALL expose a `matchSummary` field on `BankTransactionType` containing `status` (`open`/`partial`/`paid`), `matchCount`, and `totalMatched` so listings can render the pill without per-row roundtrips.

#### Scenario: Listing returns summary
- **WHEN** the frontend queries `bankTransactions { items { id matchSummary { status matchCount totalMatched } } }`
- **THEN** each item includes the computed summary derived from its `invoice_matches`
