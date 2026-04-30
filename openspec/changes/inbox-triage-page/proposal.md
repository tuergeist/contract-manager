## Why

Heute sind Banking, Incoming Invoices und Outgoing Invoices drei separate Pages, jede mit eigener Filter- und Workflow-Logik. Der User muss zwischen ihnen pendeln, um den täglichen "neue Rechnungen + neue Banktransaktionen + Zuordnen"-Loop abzuarbeiten. Eine zentrale **Inbox-Triage-Page** vereinheitlicht alle "braucht Hand-anlegen"-Items in einer chronologischen Liste mit Inline-Actions.

## What Changes

- Neue Route `/inbox` (Default-Landing für Banking-Modul, mit Sidebar-Eintrag und Badge-Counter ungematchter Items)
- Neue Backend-Query `inboxItems(limit, offset, kinds)` die ein Union-Type zurückgibt:
  - `incoming-needs-review`: Eingangsrechnung mit Status `extracted` (AI-Output prüfen)
  - `incoming-needs-cp`: Confirmed Eingangsrechnung ohne Counterparty
  - `tx-unmatched-credit`: ungematchte eingehende Banktransaktion
  - `tx-unmatched-debit`: ungematchte ausgehende Banktransaktion
- Frontend: `<InboxTriagePage>` mit `<TriageRow>`-Components
  - PDF-Thumbnail links (für Rechnungen) oder Tx-Icon
  - Felder editierbar inline
  - Inline-Action-Buttons rechts: "Confirm + Match" (Hauptaktion, grün, wenn eindeutiger Kandidat) / "Edit" (öffnet Side-Sheet) / "Skip"
- Sortierung: nach AI-Confidence asc (unsicheres zuerst), dann nach Datum desc
- Toast-basiertes Undo: nach Skip/Confirm 5s "Rückgängig" möglich
- Setzt `confirm-and-match-mutation` (#9), `ai-extraction-confidence-fields` (#10), `counterparty-combobox-shared` (#7) voraus

## Capabilities

### New Capabilities
- `inbox-triage`: Definiert die zentrale Triage-Anforderungen für ungematchte/zu-bestätigende Items aus Banking, Incoming und Outgoing

### Modified Capabilities
- Keine

## Impact

- **Backend**: 1 neue Query + Union-Resolver, evtl. Counter-Query für Sidebar-Badge
- **Frontend**: 1 neue Page (~400 LOC), `<TriageRow>`-Component (~250 LOC)
- **Routing**: neuer Eintrag in `App.tsx`, Sidebar-Eintrag in `Sidebar.tsx` + `searchablePages`-Update
- **i18n**: ~15 neue Keys für Aktionen und Status
- **E2E**: 1 neuer Playwright-Spec für die Triage-Flows
