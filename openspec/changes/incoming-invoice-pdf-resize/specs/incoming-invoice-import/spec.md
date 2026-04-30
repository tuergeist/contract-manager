## ADDED Requirements

### Requirement: Responsive PDF preview height
The system SHALL render the incoming invoice PDF preview at a viewport-relative height (70% min, 80% max) and allow the user to vertically resize it.

#### Scenario: Default height on first open
- **WHEN** the user opens the detail sheet for the first time
- **THEN** the PDF iframe is rendered at `min-h-[70vh]`

#### Scenario: User resizes height
- **WHEN** the user drags the vertical resize-grip below the iframe
- **THEN** the iframe height changes accordingly and the new height is persisted in `localStorage`

#### Scenario: Persisted height on next open
- **WHEN** the user reopens the detail sheet after resizing in a previous session
- **THEN** the iframe is restored to the previously chosen height

#### Scenario: Wider sheet for better PDF readability
- **WHEN** the detail sheet renders on screens ≥ 640px wide
- **THEN** the sheet is `sm:max-w-3xl` (768px), 96px wider than before

#### Scenario: Mobile fallback
- **WHEN** the viewport is < 640px wide
- **THEN** the sheet collapses to full-width and the PDF iframe height clamps to viewport height
