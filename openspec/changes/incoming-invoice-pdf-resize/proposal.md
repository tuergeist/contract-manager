## Why

Der PDF-Preview im `IncomingInvoiceDetail`-Sheet ist heute starr 600px hoch. Bei 2xl-Sheet-Breite (672px) und langen Rechnungen muss der User dauernd im iframe scrollen, statt das Sheet selbst zu nutzen. Außerdem gibt es keine Möglichkeit, mehr Höhe für den PDF-Viewer zu gewinnen.

## What Changes

- iframe-Höhe von `h-[600px]` auf `min-h-[70vh] max-h-[80vh]` umstellen — passt sich der Bildschirmhöhe an
- **Resize-Grip** unten am iframe (per CSS `resize: vertical`), persistiert die zuletzt gewählte Höhe pro User in `localStorage` (Key `cm:incoming:pdfHeight`)
- Sheet-Breite von `sm:max-w-2xl` auf `sm:max-w-3xl` erhöhen, damit das PDF mehr horizontal Platz hat ohne zu schrumpfen
- Buttons "Open in Tab" / "Open in Popup" bleiben unverändert (heute schon vorhanden)

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `incoming-invoice-import`: PDF-Preview-Anforderungen erweitert um responsive Höhe und User-Resize

## Impact

- **Frontend**: `frontend/src/features/incoming-invoices/IncomingInvoiceDetail.tsx` (~5 Zeilen)
- **Backend**: keine Änderung
- **i18n**: keine
