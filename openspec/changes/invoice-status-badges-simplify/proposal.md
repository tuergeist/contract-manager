## Why

Die Eingangsrechnungen-Liste zeigt heute 6 Backend-States (`pending`, `extracting`, `extracted`, `confirmed`, `matched`, `extraction_failed`) als gleichwertige Status-Badges. Für den User sind aber nur 3 Zustände entscheidungsrelevant: **Prüfen** (AI-Output muss verifiziert werden), **Bereit** (bestätigt, wartet auf Match), **Erledigt** (gematcht). Die anderen drei sind technische Loading-/Fehler-States, die nicht denselben visuellen Stellenwert verdienen.

## What Changes

- Mapping von Backend-Status auf 3 User-States:
  - `pending` + `extracting` → kleines Spinner-Icon (kein Badge), "AI arbeitet"
  - `extracted` → Badge "Prüfen" (gelb)
  - `confirmed` → Badge "Bereit" (blau)
  - `matched` → Badge "Erledigt" (grün)
  - `extraction_failed` → Badge "Fehler" (rot, mit Retry-Button)
- Filter-Dropdown vereinfacht analog: 3 Hauptfilter + Toggle "Auch fehlerhafte zeigen"
- Badge-Text in i18n vereinheitlicht (DE + EN)

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `incoming-invoice-import`: Status-Darstellung in UI vereinfacht; Backend-States bleiben unverändert (Mapping nur in Frontend)

## Impact

- **Frontend**: `frontend/src/features/incoming-invoices/IncomingInvoicesPage.tsx` (Badge-Logik + Filter)
- **Backend**: keine Änderung
- **i18n**: ~6 Keys konsolidieren auf 3
