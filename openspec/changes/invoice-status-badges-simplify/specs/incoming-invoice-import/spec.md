## ADDED Requirements

### Requirement: Simplified status display in incoming invoice list
The system SHALL display incoming invoice status using a 3-tier user-facing taxonomy ("Review", "Ready", "Done"), plus a separate "Error" state, with in-progress states represented as a spinner instead of a badge.

#### Scenario: Status mapping
- **WHEN** the list renders any invoice
- **THEN** statuses are mapped as: `pending` and `extracting` → spinner only; `extracted` → "Review" badge (yellow); `confirmed` → "Ready" badge (blue); `matched` → "Done" badge (green); `extraction_failed` → "Error" badge (red)

#### Scenario: Filter dropdown options
- **WHEN** the user opens the status filter dropdown
- **THEN** the visible options are "Alle / All", "Review", "Ready", "Done"; "Error" appears as a separate toggle "Auch fehlerhafte zeigen / Show errors" (default on)

#### Scenario: Filter values map to backend statuses
- **WHEN** the user selects "Review"
- **THEN** the backend receives `status=extracted` filter value

#### Scenario: Backwards-compatible deep-links
- **WHEN** an existing URL contains `?status=extracted`
- **THEN** the page still respects this filter; the dropdown shows "Review" as selected
