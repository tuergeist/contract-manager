## Why

Die AI-Extraktion gibt heute einen JSON-Block mit Feldern zurück (supplier_name, gross_amount usw.) — der User sieht nicht, welche Felder unsicher waren. Im Self-Guard-Fall (Tenant als Supplier zurückgegeben) wäre eine sichtbare Confidence-Warnung am Feld hilfreich. Generell: User-Trust steigt, wenn er weiß was er prüfen muss vs. was zuverlässig ist.

## What Changes

- Erweiterung des Extraction-Prompts: zusätzlich zu jedem Feld ein `*_confidence`-Wert von 0.0–1.0 zurückgeben (geschachtelt:`{"supplier_name": "...", "supplier_name_confidence": 0.92, ...}`)
- Backend-Modell: neue JSON-Spalte `extraction_confidence` auf `IncomingInvoice` (Migration)
- GraphQL: `extractionConfidence: JSON` auf `IncomingInvoiceType`
- Frontend: in `IncomingInvoiceDetail` Felder mit `confidence < 0.8` bekommen einen gelben Border + Tooltip "AI ist unsicher — bitte prüfen"
- Confidence-Werte werden außerdem für die geplante Inbox-Triage-Page genutzt (Items mit niedriger Confidence priorisiert anzeigen)

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `incoming-invoice-import`: AI-Extraction-Ergebnisse beinhalten jetzt Confidence-Werte; UI markiert unsichere Felder visuell

## Impact

- **Backend**: Migration (1 JSON-Feld), Prompt-Update, Tests
- **Frontend**: `IncomingInvoiceDetail.tsx` (Field-Component mit Confidence-Hint)
- **Token-Kosten**: minimal (~10% mehr Output-Tokens pro Extraktion)
- **Bestehende Daten**: alte Rechnungen bleiben ohne Confidence — UI rendert dann normal (kein Hint)
