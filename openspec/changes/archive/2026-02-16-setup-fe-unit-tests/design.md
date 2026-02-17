## Context

The frontend has vitest, @testing-library/react, @testing-library/jest-dom, and jsdom listed in devDependencies but no configuration or test files exist. The `test` script in package.json runs `vitest` but there's no `vitest.config.ts`. The vite config at `vite.config.ts` has no test block.

Target test areas (from analysis):
- Pure functions in `lib/utils.ts` (formatDate, formatCurrency, formatMonthYear, formatDateTime)
- Route matcher in `lib/helpVideoLinks.ts` (matchRoute)
- `usePersistedState` custom hook (localStorage persistence)
- `ForecastsPage` component (permission gating, tab URL params)
- Sidebar nav filtering (permission-based filtering)

## Goals / Non-Goals

**Goals:**
- Working vitest configuration with jsdom, path aliases, and setup files
- Reusable test utilities for rendering components with mocked auth context
- Unit tests for the 5 target areas listed above
- Tests run locally via `npm run test` and in CI via `make test-front`

**Non-Goals:**
- Replacing Playwright E2E tests
- Testing third-party Shadcn/ui components
- Mocking the full Apollo GraphQL layer (Apollo MockedProvider is heavy — only use where necessary)
- Testing large page components (ContractDetail, InvoiceList)

## Decisions

### 1. Vitest config approach

**Decision:** Create a standalone `vitest.config.ts` that extends the existing vite config for path aliases but adds test-specific settings (jsdom environment, setup files, coverage).

**Rationale:** Keeps production vite config clean. Vitest natively supports referencing vite config for resolve aliases.

### 2. Auth mock strategy

**Decision:** Create a `renderWithAuth` test utility that wraps components in a minimal `AuthContext.Provider` with configurable user/permissions, bypassing `AuthProvider` and Apollo entirely.

**Rationale:** `hasPermission` just checks `user.permissions.includes(...)`. Providing a mock context with a permissions array is simpler and faster than mocking the Apollo client + ME_QUERY chain. Components under test only need `useAuth()` to return controlled values.

### 3. Router mock strategy

**Decision:** Use `MemoryRouter` from react-router-dom for components that use `useSearchParams` or `<Link>`. Set initial entries to control URL state.

**Rationale:** MemoryRouter is the standard testing approach for react-router — no need for additional mocking.

### 4. Test file location

**Decision:** Co-locate test files next to source files (`utils.test.ts` next to `utils.ts`, `ForecastsPage.test.tsx` next to `ForecastsPage.tsx`).

**Rationale:** Easier to find tests, standard vitest convention, and keeps imports short.

### 5. What NOT to mock

**Decision:** Test pure functions directly with no mocking. Only mock auth context and router for component tests. Do not mock Apollo — component tests that need data should test rendering logic with pre-set props/context, not GraphQL responses.

## Risks / Trade-offs

- **ForecastsPage renders child components** → Test checks that the right child renders based on permission, not that the child works correctly. Child components will attempt to use Apollo hooks — we may need to mock `useQuery` or wrap in MockedProvider with empty data to avoid errors.
- **Sidebar uses `useAuth` and `useNavigate`** → Need both auth mock and MemoryRouter wrappers, slight test setup complexity.
