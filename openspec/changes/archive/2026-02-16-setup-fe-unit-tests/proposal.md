## Why

The frontend has zero unit tests — only Playwright E2E tests exist. Vitest and testing-library are installed but unconfigured. Critical logic (permission gating, URL routing, data formatting) relies entirely on E2E coverage, which is slow and coarse. Unit tests for high-value utility functions and recently added components would catch regressions faster and more precisely.

## What Changes

- Configure vitest with jsdom environment and test setup files
- Create test utilities (Apollo mock provider, auth mock, render helpers)
- Add unit tests for pure utility functions (`matchRoute`, `formatCurrency`, `formatDate`)
- Add unit tests for `ForecastsPage` (permission gating, tab routing, URL params)
- Add unit tests for Sidebar permission filtering
- Add unit tests for `usePersistedState` localStorage hook

## Capabilities

### New Capabilities
- `fe-test-infrastructure`: Vitest configuration, test setup files, mock providers, and render utilities
- `fe-unit-tests`: Unit tests for utility functions, permission-gated components, and custom hooks

### Modified Capabilities
_(none — no existing behavior changes, only adding tests)_

## Impact

- **New files**: `vitest.config.ts`, `src/test/setup.ts`, `src/test/utils.tsx`, test files (`*.test.ts`, `*.test.tsx`)
- **Modified files**: `package.json` (test scripts), possibly `tsconfig.json` (include test files)
- **No production code changes** — tests only
