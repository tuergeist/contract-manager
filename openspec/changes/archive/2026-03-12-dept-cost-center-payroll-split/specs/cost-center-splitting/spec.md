## ADDED Requirements

### Requirement: FTE distribution split mode in split rules

The split rule system SHALL support a third mode "fte_distribution" alongside "percentage" and "fixed_amount". FTE distribution rules have no manually defined allocations — they are resolved dynamically.

#### Scenario: Create FTE distribution rule
- **WHEN** user creates a split rule with mode "fte_distribution" for a counterparty
- **THEN** the rule SHALL be saved without any allocation entries
- **AND** the UI SHALL show "Split by FTE distribution" as the rule description

#### Scenario: FTE rule in rule list
- **WHEN** user views the split rules list
- **THEN** FTE distribution rules SHALL display "FTE distribution" as their type instead of showing allocation percentages

#### Scenario: Edit FTE rule
- **WHEN** user edits an FTE distribution rule
- **THEN** the user SHALL only be able to change the counterparty/pattern and priority (no allocation editing)

#### Scenario: Validate FTE rule prerequisites
- **WHEN** user creates an FTE distribution rule but no departments have linked cost centers
- **THEN** the system SHALL warn "No departments have linked cost centers — FTE split will have no effect"

## MODIFIED Requirements

### Requirement: Define cost center split rules
The system SHALL allow users to define rules that automatically split transactions or incoming invoices across multiple cost centers. Rules are defined per counterparty or per booking text pattern. Rules can use percentage-based, fixed-amount, or FTE-distribution mode.

#### Scenario: Percentage-based split rule for counterparty
- **WHEN** user creates a rule for counterparty "AWS" splitting 60% to cost center "100 — Engineering" and 40% to "200 — Marketing"
- **THEN** transactions from "AWS" are automatically split accordingly

#### Scenario: Fixed-amount split rule
- **WHEN** user creates a rule for counterparty "Telekom" splitting €50 to "300 — Office" and the remainder to "100 — Engineering"
- **THEN** a €200 transaction from Telekom assigns €50 to "300" and €150 to "100"

#### Scenario: FTE distribution split rule
- **WHEN** user creates a rule for counterparty "Payroll Provider" with mode "fte_distribution"
- **THEN** transactions from "Payroll Provider" are automatically split using the FTE distribution for the transaction's month (snapshot if available, live data otherwise)

#### Scenario: Booking text pattern rule
- **WHEN** user creates a rule matching booking text containing "HOSTING" splitting 100% to "100 — Engineering"
- **THEN** any transaction (regardless of counterparty) with "HOSTING" in booking text is assigned to cost center "100"

#### Scenario: Split percentages must total 100%
- **WHEN** user creates a percentage-based split rule with 60% to "100" and 30% to "200" (totaling 90%)
- **THEN** the system rejects the rule with a validation error

#### Scenario: Rule priority
- **WHEN** a transaction matches both a counterparty rule and a booking text pattern rule
- **THEN** the counterparty-specific rule takes priority over the pattern rule
