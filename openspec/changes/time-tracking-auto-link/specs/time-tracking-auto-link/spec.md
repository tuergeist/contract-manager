## ADDED Requirements

### Requirement: Auto-link rules can be configured per contract
The system SHALL allow users to create pattern-based auto-link rules on a contract. Each rule defines a pattern that matches against external time tracking project names. A contract MAY have multiple auto-link rules.

#### Scenario: Create an auto-link rule with substring pattern
- **WHEN** user adds an auto-link rule on a contract with pattern `[KSB DL-Vertrag]` and match type "contains"
- **THEN** the rule is saved and associated with the contract

#### Scenario: Create an auto-link rule targeting a specific contract item
- **WHEN** user adds an auto-link rule and selects a delivery item from the contract
- **THEN** the rule is saved with the contract item reference, and auto-linked projects will be mapped to that item

#### Scenario: Create an auto-link rule with prefix pattern
- **WHEN** user adds an auto-link rule with pattern `KSB-` and match type "starts_with"
- **THEN** the rule matches any project whose name starts with `KSB-`

#### Scenario: Delete an auto-link rule
- **WHEN** user deletes an auto-link rule
- **THEN** the rule is removed but existing mappings created by that rule remain intact

### Requirement: Background sync auto-links matching projects daily
The system SHALL run a daily background task that fetches all projects from the time tracking provider, evaluates them against all active auto-link rules, and creates mappings for new matches. The task SHALL run as part of the existing Celery Beat schedule.

#### Scenario: New project matches an auto-link rule
- **WHEN** the daily sync runs and a project named `[KSB DL-Vertrag] Maintenance Q1` exists that matches a rule with pattern `[KSB DL-Vertrag]` (contains)
- **THEN** the system creates a TimeTrackingProjectMapping linking this project to the rule's contract (and contract item if specified)

#### Scenario: Already-linked project is skipped
- **WHEN** the daily sync runs and a matching project is already linked to the contract (whether manually or via auto-link)
- **THEN** no duplicate mapping is created

#### Scenario: Project matches multiple rules on different contracts
- **WHEN** a project name matches auto-link rules on two different contracts
- **THEN** the system creates a mapping for the first matching rule only (by rule creation order) since a project can only be mapped once (unique constraint on external_project_id per tenant)

#### Scenario: No time tracking provider configured
- **WHEN** the daily sync runs for a tenant with no time tracking provider configured
- **THEN** the tenant's auto-link rules are skipped without error

### Requirement: Auto-linked mappings are distinguishable from manual ones
The system SHALL track whether a mapping was created manually or by an auto-link rule. This allows users to see how each mapping was created.

#### Scenario: Auto-linked mapping shows source
- **WHEN** a mapping is created by the auto-link sync
- **THEN** the mapping's link source is recorded as "auto" and the originating rule is referenced

#### Scenario: Manual mapping shows source
- **WHEN** a mapping is created via the existing manual linking flow
- **THEN** the mapping's link source is recorded as "manual" (or null for backwards compatibility)

### Requirement: Preview which projects would match a rule
The system SHALL provide a way to preview which unlinked projects would match a given pattern before saving the rule. This helps users verify their pattern is correct.

#### Scenario: Preview shows matching projects
- **WHEN** user enters pattern `[KSB` with match type "contains" and clicks preview
- **THEN** the system shows a list of unlinked projects whose names contain `[KSB`

#### Scenario: Preview shows no matches
- **WHEN** user enters a pattern that matches no unlinked projects
- **THEN** the system shows an empty state indicating no projects match

### Requirement: Auto-link rules are displayed in the contract detail
The system SHALL display auto-link rules in the contract detail view alongside existing manual time tracking mappings. Users SHALL be able to add, view, and delete rules from this location.

#### Scenario: Rules shown alongside mappings
- **WHEN** user views a contract that has auto-link rules
- **THEN** the rules are displayed in the time tracking section, visually distinct from manual mappings

#### Scenario: Empty state when no rules exist
- **WHEN** user views a contract with no auto-link rules
- **THEN** an option to add an auto-link rule is available in the time tracking section
