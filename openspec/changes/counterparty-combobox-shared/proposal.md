## Why

An drei Stellen im Frontend gibt es nahezu identische Counterparty-Picker (Popover + Command + Search + Create-New): `BankingPage.tsx`, `IncomingInvoicesPage.tsx`, `IncomingInvoiceDetail.tsx`. Drei Copy-Paste-Implementierungen bedeuten dreifache Bug-Surface, inkonsistente UX und hohe Wartungskosten. Außerdem blockiert dieser Code die geplante Inbox-Triage-Page (würde Picker #4 werden).

## What Changes

- Neue Shared-Komponente `frontend/src/components/CounterpartyCombobox.tsx`:
  ```tsx
  <CounterpartyCombobox
    value={counterpartyId}
    onChange={(id, cp) => ...}
    allowCreate={true}
    placeholder="Lieferant suchen..."
    customerOnly={false}      // optional: nur Kunden-verknüpfte
    excludeTenantSelf={true}  // Tenant-Eigen ausschließen
  />
  ```
- Backend-Query, Debounce, "Create new"-Modal werden intern gekapselt
- Bestehende drei Aufrufstellen migrieren auf die neue Komponente
- Visuelle Konsistenz: gleiche Keyboard-Navigation, gleiche Search-Latenz, gleiche Create-Bestätigung

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `banking-counterparty-date-filter`: keine direkte Änderung (interner Refactor)
- `incoming-invoice-import`: Counterparty-Picker im Detail/Listing wird durch shared Component ersetzt — keine Verhaltens-Änderung erwartet

## Impact

- **Frontend**: 1 neue Komponente (~250 LOC), Migration in 3 Files (jeweils ~80–100 LOC weniger)
- **Backend**: keine Änderung
- **Tests**: Vitest-Tests für `CounterpartyCombobox` (Suche, Create, Tenant-Self-Exclude); E2E-Tests der drei Pages bleiben grün
