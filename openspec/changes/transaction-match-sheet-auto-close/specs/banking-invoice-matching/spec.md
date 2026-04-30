## ADDED Requirements

### Requirement: Auto-close match sheet on full match
The system SHALL automatically close the transaction match sheet shortly after the user creates a match that fully reconciles the transaction amount.

#### Scenario: Full match closes the sheet
- **WHEN** the user creates a match such that `abs(transaction.amount) - totalMatched < 0.01`
- **THEN** the sheet automatically closes after a brief delay (≈ 400ms) so the user can see the "fully matched" confirmation

#### Scenario: Partial match keeps the sheet open
- **WHEN** the user creates a match that only partially covers the transaction amount
- **THEN** the sheet stays open so the user can add additional matches

#### Scenario: User can disable auto-close
- **WHEN** the user toggles "Auto-close match sheet" off in their settings
- **THEN** the sheet stays open even on full match, regardless of match completeness

#### Scenario: Undo toast on auto-close
- **WHEN** the sheet auto-closes after a match
- **THEN** a toast notification appears for 5 seconds with a "Rückgängig" / "Undo" action that deletes the just-created match and reopens the sheet

#### Scenario: Race-safe close
- **WHEN** between the 400ms delay and actual close the user adds another match that changes total matched
- **THEN** the system re-evaluates the close condition before closing; if no longer fully matched, the close is cancelled
