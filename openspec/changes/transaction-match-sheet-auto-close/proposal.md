## Why

Wenn ein User in `TransactionMatchSheet` eine Banktransaktion vollständig matcht (Differenz < 0,01 €), bleibt das Sheet offen. Der User muss manuell schließen, in der Liste die nächste ungematchte Tx finden, anklicken — ein vermeidbarer Reibungspunkt im Massen-Matching-Flow.

## What Changes

- Nach erfolgreichem `createMatch` prüfen, ob Tx jetzt voll gematcht ist (`abs(amount) === totalMatched`)
- Wenn ja: Sheet automatisch schließen (mit kurzer 400ms Delay, damit der User die "Fully matched"-Bestätigung sieht)
- Optional: Toast-Notification "Tx erledigt — 14 weitere ungematcht" mit Aktion "Nächste öffnen"
- Verhalten lässt sich per User-Setting deaktivieren (Default: an)

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `banking-invoice-matching`: Erweitert die Sheet-Lifecycle-Anforderungen um automatisches Schließen bei vollem Match

## Impact

- **Frontend**: `frontend/src/features/banking/TransactionMatchSheet.tsx` (in `handleAddMatch`), neue Setting in `UserSettings`
- **Backend**: keine Änderung
- **i18n**: 1 neuer Toast-Key
