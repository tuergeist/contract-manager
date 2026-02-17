## ADDED Requirements

### Requirement: Utility functions have unit tests
The project SHALL have unit tests for `formatDate`, `formatDateTime`, `formatMonthYear`, and `formatCurrency` in `lib/utils.ts`.

#### Scenario: formatDate handles null and undefined
- **WHEN** `formatDate(null)` or `formatDate(undefined)` is called
- **THEN** it returns `'-'`

#### Scenario: formatDate formats valid date string
- **WHEN** `formatDate('2026-03-15')` is called
- **THEN** it returns `'15.03.2026'`

#### Scenario: formatCurrency handles null and undefined
- **WHEN** `formatCurrency(null)` or `formatCurrency(undefined)` is called
- **THEN** it returns `'-'`

#### Scenario: formatCurrency formats EUR value
- **WHEN** `formatCurrency(1234.56)` is called
- **THEN** it returns a string containing `1.234,56` and `€`

#### Scenario: formatCurrency supports compact notation
- **WHEN** `formatCurrency(1500000, { compact: true })` is called
- **THEN** it returns a compact string like `1,5 Mio. €`

### Requirement: matchRoute has unit tests
The project SHALL have unit tests for `matchRoute` in `lib/helpVideoLinks.ts`.

#### Scenario: Exact path match
- **WHEN** `matchRoute('/customers', '/customers')` is called
- **THEN** it returns `true`

#### Scenario: Param segment match
- **WHEN** `matchRoute('/customers/:id', '/customers/123')` is called
- **THEN** it returns `true`

#### Scenario: Length mismatch rejects
- **WHEN** `matchRoute('/customers/:id', '/customers')` is called
- **THEN** it returns `false`

#### Scenario: Different paths reject
- **WHEN** `matchRoute('/products', '/customers')` is called
- **THEN** it returns `false`

### Requirement: usePersistedState has unit tests
The project SHALL have unit tests for the `usePersistedState` hook.

#### Scenario: Returns default when localStorage is empty
- **WHEN** hook is called with key `'test'` and default `'hello'`
- **THEN** it returns `'hello'`

#### Scenario: Reads existing value from localStorage
- **WHEN** localStorage has `'test'` set to `'"world"'`
- **AND** hook is called with key `'test'` and default `'hello'`
- **THEN** it returns `'world'`

#### Scenario: Falls back to default on corrupt JSON
- **WHEN** localStorage has `'test'` set to `'{invalid'`
- **AND** hook is called with key `'test'` and default `'hello'`
- **THEN** it returns `'hello'`

### Requirement: ForecastsPage has unit tests
The project SHALL have unit tests for the `ForecastsPage` component covering permission gating and tab behavior.

#### Scenario: Shows only revenue when no banking permission
- **WHEN** user lacks `banking.read` permission
- **THEN** ForecastsPage renders RevenueForecast without tab switcher

#### Scenario: Shows tabs when user has banking permission
- **WHEN** user has `banking.read` permission
- **THEN** ForecastsPage renders tab buttons for Revenue and Liquidity

#### Scenario: Revenue tab active by default
- **WHEN** URL has no `tab` search parameter
- **THEN** Revenue tab is active

#### Scenario: Liquidity tab active from URL
- **WHEN** URL has `?tab=liquidity`
- **THEN** Liquidity tab is active

### Requirement: Sidebar permission filtering has unit tests
The project SHALL have unit tests verifying that Sidebar filters nav items based on user permissions.

#### Scenario: Items without permission requirement always show
- **WHEN** user has no permissions
- **THEN** nav items without a `permission` field (Dashboard, Contracts, etc.) are rendered

#### Scenario: Permission-gated items hidden without permission
- **WHEN** user lacks `invoices.read` permission
- **THEN** the Invoices nav link is not rendered

#### Scenario: Permission-gated items shown with permission
- **WHEN** user has `invoices.read` permission
- **THEN** the Invoices nav link is rendered
