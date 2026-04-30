## ADDED Requirements

### Requirement: Default invoice list when suggestions are empty
The system SHALL display a fallback list of recent unmatched invoices in the transaction match sheet when no specific suggestions are available, so users can browse without typing a search.

#### Scenario: No suggestions but recent unmatched exist
- **WHEN** the transaction has no suggested matches (no customer link, no counterparty match)
- **THEN** the sheet renders up to 10 recent unmatched invoices from the last 30 days as default suggestions

#### Scenario: Debit transaction shows incoming invoices
- **WHEN** the transaction is a debit (outgoing payment)
- **THEN** the default list contains incoming invoices with status `extracted` or `confirmed` and no full payment match

#### Scenario: Credit transaction shows outgoing invoices
- **WHEN** the transaction is a credit (incoming payment)
- **THEN** the default list contains outgoing invoices (imported or generated) with outstanding balance

#### Scenario: Counterparty-aware default
- **WHEN** the transaction has a known counterparty but no linked customer
- **THEN** the default list is filtered to invoices belonging to that counterparty (where applicable)

#### Scenario: User starts typing
- **WHEN** the user types ≥ 2 characters in the search field
- **THEN** the search results replace the default list

#### Scenario: User clears search
- **WHEN** the user clears the search field
- **THEN** the default list is restored

#### Scenario: More results than shown
- **WHEN** more than 10 unmatched invoices exist for the criteria
- **THEN** a hint "+ N weitere — über Suche eingrenzen" is rendered below the default list
