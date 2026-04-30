## ADDED Requirements

### Requirement: Confirm-and-advance workflow
The system SHALL provide a "Confirm + Next" action in the incoming invoice detail view that confirms the current invoice and immediately loads the next pending invoice in the same view.

#### Scenario: Confirm and advance to next pending invoice
- **WHEN** the user clicks "Confirm + Next" on a pending invoice
- **THEN** the current invoice is marked as confirmed AND the detail view replaces its content with the next pending invoice in the current sort order

#### Scenario: Auto-close when no further pending invoices remain
- **WHEN** the user clicks "Confirm + Next" on the last pending invoice in the current filtered list
- **THEN** the current invoice is confirmed AND the detail view closes AND a toast notification "All incoming invoices processed" appears

#### Scenario: Pending list respects current page filter
- **WHEN** the user has filtered the list to status "needs review" and confirms an invoice
- **THEN** the next loaded invoice is from the same filtered set, not the global list

#### Scenario: Keyboard shortcut triggers confirm-and-advance
- **WHEN** the detail view is open and the user presses `Cmd+Enter` (macOS) or `Ctrl+Enter` (other platforms)
- **THEN** the same confirm-and-advance behavior is triggered as clicking the button

#### Scenario: Same invoice not re-shown immediately after confirm
- **WHEN** an invoice is confirmed but remains in the pending set (e.g., still missing counterparty)
- **THEN** the detail view does not loop back to it within the same advance action; it advances strictly to a different invoice or closes

#### Scenario: Standard "Confirm" button retained
- **WHEN** the user wishes to confirm without advancing
- **THEN** the standard "Confirm" button still works as before, leaving the detail view open on the current invoice
