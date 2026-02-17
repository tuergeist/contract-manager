## 1. Vitest configuration

- [x] 1.1 Create `frontend/vitest.config.ts` with jsdom environment, path aliases from vite.config.ts, setup file reference, and include pattern `**/*.test.{ts,tsx}`
- [x] 1.2 Create `frontend/src/test/setup.ts` that imports `@testing-library/jest-dom`
- [x] 1.3 Add `src/test` to tsconfig.json `include` if needed for type resolution (already covered by `["src"]`)

## 2. Test utilities

- [x] 2.1 Create `frontend/src/test/utils.tsx` with `renderWithAuth` that wraps components in mocked AuthContext.Provider and MemoryRouter, accepting `permissions`, `user`, and `route` options
- [x] 2.2 Export a `createMockUser` helper that returns a default User object with overridable fields

## 3. Utility function tests

- [x] 3.1 Create `frontend/src/lib/utils.test.ts` with tests for `formatDate` (null, undefined, valid date)
- [x] 3.2 Add tests for `formatDateTime` (null, valid datetime)
- [x] 3.3 Add tests for `formatMonthYear` (null, valid date)
- [x] 3.4 Add tests for `formatCurrency` (null, undefined, normal value, compact notation)

## 4. matchRoute tests

- [x] 4.1 Create `frontend/src/lib/helpVideoLinks.test.ts` — export `matchRoute` and test: exact match, param segment match, length mismatch, different paths

## 5. usePersistedState tests

- [x] 5.1 Create `frontend/src/lib/usePersistedState.test.ts` with tests: default value when empty, reads stored value, falls back on corrupt JSON, writes state to localStorage

## 6. ForecastsPage tests

- [x] 6.1 Create `frontend/src/features/forecasts/ForecastsPage.test.tsx` — test: renders only RevenueForecast without banking permission (no tabs visible), renders both tabs with banking permission, revenue tab active by default, liquidity tab active from URL param

## 7. Sidebar tests

- [x] 7.1 Create `frontend/src/components/Sidebar.test.tsx` — test: unpermissioned items always render, permission-gated items hidden without permission, permission-gated items shown with permission

## 8. Verification

- [x] 8.1 Run `npm run test` and verify all tests pass (35/35)
- [x] 8.2 Run `npx tsc --noEmit` to verify no TypeScript errors
