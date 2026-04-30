## Why

Power-User (Buchhalter, die täglich 30+ Items abarbeiten) sind mit Maus-Workflows ineffizient. Vim-style Keyboard-Shortcuts (`j/k` für Navigation, single-letter Actions) erlauben es, eine Triage-Session in einem Bruchteil der Zeit zu erledigen. Übliche Patterns aus Linear, GitHub, Superhuman.

## What Changes

- In der `<InboxTriagePage>` und `<TriageRow>`:
  - `j` / `k`: nächstes / voriges Item
  - `Enter`: aktives Item öffnen (Detail-Sheet)
  - `c`: Confirm (für Eingangsrechnungen)
  - `m`: Match — öffnet Match-Sheet oder bestätigt Auto-Match-Suggestion
  - `s`: Skip — markiert als später / verschiebt ans Ende
  - `e`: Edit — Counterparty-Picker / Inline-Edit
  - `?`: Hilfe-Overlay mit allen Shortcuts
- Visueller Fokus-Indicator (gelber Border) auf aktivem Item
- Shortcuts deaktiviert wenn Detail-Sheet, Modal oder Input-Field offen
- Keyboard-Hints am rechten Rand der Buttons (z.B. `[c] Confirm`, `[m] Match`)

## Capabilities

### New Capabilities
- `triage-keyboard`: Definiert Keyboard-Navigation für die Inbox-Triage

### Modified Capabilities
- Keine

## Impact

- **Frontend**: Custom Hook `useTriageShortcuts(items, handlers)` (~80 LOC), Hilfe-Overlay-Component (~50 LOC)
- **Backend**: keine Änderung
- **Accessibility**: ARIA-Live-Region für Aktionen, Focus-Management nach Confirm/Skip
- **i18n**: 1 Hilfe-Page mit allen Shortcuts in DE/EN
- **Setzt voraus**: `inbox-triage-page` (#12)
