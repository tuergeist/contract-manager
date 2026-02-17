## ADDED Requirements

### Requirement: Dashboard does not display team todos
The dashboard SHALL NOT display the team todos section or issue a GraphQL query for team todos.

#### Scenario: Dashboard loads without team todos query
- **WHEN** the dashboard page loads
- **THEN** only two GraphQL queries SHALL be issued: `DashboardKPIs` and `MyTodos`

#### Scenario: Team todos not rendered
- **WHEN** the dashboard page is displayed
- **THEN** no "Team Todos" heading or team todo list SHALL be visible

### Requirement: My todos section uses full width
The my todos section on the dashboard SHALL span the full width of the content area instead of a half-width grid column.

#### Scenario: Full-width todo list
- **WHEN** the dashboard page is displayed
- **THEN** the my todos section SHALL not be constrained to a two-column grid layout
