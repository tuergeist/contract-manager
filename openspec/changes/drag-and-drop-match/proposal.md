## Why

Klassisches Klick-Matching ist mental belastend: User klickt Tx → Sheet öffnet → Liste durchsuchen → Klick. Drag-and-drop nutzt direkte räumliche Manipulation und ist bei vielen Items (15+ Tx auf einer Page) deutlich schneller. Außerdem: visuell befriedigend, baut Vertrauen in's System.

## What Changes

- In der `<InboxTriagePage>` (oder als Erweiterung der `BankTransactionsTab`):
  - Tx-Karten und Invoice-Karten werden mit `@dnd-kit` draggable
  - Drag einer Tx auf eine Invoice-Karte → öffnet Confirmation-Modal "Match 805,93 € an Rechnung 2026/10580?" mit zusätzlichem Differenz-Hint
  - Bestätigung → `createPaymentMatch` Mutation
  - Drag einer Invoice auf eine Tx funktioniert symmetrisch
- Visuelles Feedback während Drag: andere Items dimmen, kompatibler Drop-Target leuchtet grün, inkompatibler rot (z.B. Currency-Mismatch)
- Keyboard-Alternative: `Space` zum "Pickup", Pfeiltasten zum Navigieren, `Space` zum Drop (ARIA-konform)
- Touch-Support für Tablets

## Capabilities

### New Capabilities
- Keine (technische UX-Erweiterung)

### Modified Capabilities
- `banking-invoice-matching`: Match-Erstellung wird zusätzlich per Drag-Drop möglich; bestehender Match-Sheet-Flow bleibt erhalten

## Impact

- **Frontend**: `@dnd-kit` ist bereits Dep — Reuse aus Contract-Item-Reorder; ca. 200 LOC neue Drag-Logic
- **Backend**: keine Änderung — gleiche Mutations
- **Performance**: dnd-kit ist leichtgewichtig; keine spürbare Last bei <100 Items pro Page
- **Tests**: Vitest-Unit-Tests + 1 E2E mit Playwright Drag-Drop
