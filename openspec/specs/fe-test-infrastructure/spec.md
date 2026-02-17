## ADDED Requirements

### Requirement: Vitest configuration exists and works
The project SHALL have a `vitest.config.ts` that configures jsdom environment, path aliases matching vite.config.ts, and setup files.

#### Scenario: Run vitest successfully
- **WHEN** developer runs `npm run test` in the frontend directory
- **THEN** vitest starts and discovers test files matching `**/*.test.{ts,tsx}`

#### Scenario: Path aliases resolve in tests
- **WHEN** a test file imports from `@/lib/utils`
- **THEN** the import resolves to `src/lib/utils` correctly

### Requirement: Test setup file configures DOM matchers
The project SHALL have a test setup file that imports `@testing-library/jest-dom` to enable matchers like `toBeInTheDocument()`.

#### Scenario: DOM matchers available in tests
- **WHEN** a test uses `expect(element).toBeInTheDocument()`
- **THEN** the assertion works without additional imports in the test file

### Requirement: Auth test utility provides mock context
The project SHALL provide a `renderWithAuth` utility that renders components inside a mocked `AuthContext.Provider` with configurable user and permissions.

#### Scenario: Render component with specific permissions
- **WHEN** test calls `renderWithAuth(<Component />, { permissions: ['banking.read'] })`
- **THEN** `useAuth().hasPermission('banking', 'read')` returns true inside the component

#### Scenario: Render component without permissions
- **WHEN** test calls `renderWithAuth(<Component />)` with no permissions specified
- **THEN** `useAuth().hasPermission(...)` returns false for any resource/action

### Requirement: Router test utility supports URL params
The `renderWithAuth` utility SHALL accept a `route` option to set the initial URL, wrapping components in `MemoryRouter`.

#### Scenario: Component reads search params
- **WHEN** test calls `renderWithAuth(<Component />, { route: '/forecasts?tab=liquidity' })`
- **THEN** `useSearchParams().get('tab')` returns `'liquidity'` inside the component
