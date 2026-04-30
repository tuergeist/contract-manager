## Why

Bestätigen einer eingehenden Rechnung ist heute eine Sackgasse: nach dem Klick auf "Confirm" bleibt das Detail-Sheet offen, der User muss manuell schließen, in der Liste die nächste pending-Rechnung suchen und neu öffnen. Bei 20 Rechnungen pro Woche sind das ~80 unnötige Klicks. Das ist der teuerste UX-Verlust der heutigen Pipeline.

## What Changes

- Neuer **"Confirm + Next"**-Button im `IncomingInvoiceDetail`-Sheet neben dem bestehenden Confirm. Er bestätigt die aktuelle Rechnung und lädt automatisch die nächste pending Rechnung im selben Sheet.
- Die Reihenfolge der "nächsten" Rechnung folgt der aktuellen Sortierung der Liste (Default: ältester pending zuerst).
- Wenn keine weitere pending Rechnung existiert, schließt das Sheet automatisch und zeigt eine kurze Toast-Bestätigung ("Alle bestätigt").
- Bestehender "Confirm"-Button bleibt — für User die explizit nicht weiternavigieren wollen.
- Keyboard-Shortcut (`Cmd+Enter` / `Ctrl+Enter`) löst "Confirm + Next" aus.

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `incoming-invoice-import`: Erweitert die Detail-Workflow-Anforderungen um eine Confirm-and-advance Aktion sowie einen Hint-Mechanismus für "next pending in current filter".

## Impact

- **Frontend**: `frontend/src/features/incoming-invoices/IncomingInvoiceDetail.tsx`, `IncomingInvoicesPage.tsx` (Page muss die "next id"-Lookup-Funktion bereitstellen)
- **Backend**: keine Änderung — die nächste ID wird clientseitig aus der bereits geladenen Liste ermittelt
- **i18n**: zwei neue Keys (`incomingInvoices.detail.confirmAndNext`, `incomingInvoices.detail.allConfirmed`)
