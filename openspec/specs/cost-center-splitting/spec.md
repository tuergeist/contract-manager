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

### Requirement: View and manage split rules
The system SHALL display all split rules in a rule editor, grouped by counterparty and by pattern.

#### Scenario: List split rules
- **WHEN** user opens the split rules page
- **THEN** all rules are displayed showing counterparty/pattern, cost center allocations, and type (percentage/fixed)

#### Scenario: Edit split rule
- **WHEN** user changes the split for "AWS" from 60/40 to 70/30
- **THEN** the rule is updated; future transactions use the new split

#### Scenario: Delete split rule
- **WHEN** user deletes a split rule
- **THEN** future transactions for that counterparty/pattern use the counterparty's default cost center (or none)

### Requirement: Manual split on individual transactions
The system SHALL allow users to manually split a single transaction or incoming invoice across multiple cost centers, overriding any automatic rule.

#### Scenario: Manual split
- **WHEN** user splits a €1,000 transaction into €600 to "100" and €400 to "200"
- **THEN** the transaction shows two cost center allocations totaling the transaction amount

#### Scenario: Manual split overrides rule
- **WHEN** a transaction has an automatic rule-based split but user manually re-splits it
- **THEN** the manual split replaces the automatic one

#### Scenario: Split amounts must equal transaction amount
- **WHEN** user tries to split a €1,000 transaction into €600 + €300
- **THEN** the system rejects the split (€900 ≠ €1,000)

### Requirement: Cost center reporting
The system SHALL provide a summary view of costs per cost center for a given period.

#### Scenario: Cost center summary
- **WHEN** user views the cost center report for January 2026
- **THEN** the system shows total debits per cost center, including split amounts

#### Scenario: Unassigned costs
- **WHEN** transactions exist without any cost center assignment
- **THEN** they appear under an "Unassigned" category in the report
