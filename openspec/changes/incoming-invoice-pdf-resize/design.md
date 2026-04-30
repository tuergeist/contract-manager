## Context

Heute ist die iframe-Höhe `h-[600px]` und die Sheet-Breite `sm:max-w-2xl` (672px). Bei 4K-Monitoren bleibt unten viel ungenutzter Platz; bei kleineren Screens (1366×768 Notebook) ist 600px schon am Anschlag.

## Goals

- Responsive iframe-Höhe basierend auf Viewport
- User kann manuell mehr Höhe gewinnen, persistiert über Sessions
- Sheet-Breite leicht erhöht für bessere PDF-Lesbarkeit

## Non-Goals

- Eingebauter PDF-Viewer mit Zoom-Steuerung — wer das braucht, nutzt "Open in Tab"
- Side-by-Side-Layout (PDF links, Form rechts)

## Decisions

### Decision 1: `min-h-[70vh] max-h-[80vh]`

70 % der Viewport-Höhe ist auf allen üblichen Bildschirmen (768p–1440p) ausreichend, ohne dass der Form-Block unten verschwindet. `max-h` verhindert dass auf 4K-Screens die iframe lächerlich groß wird.

### Decision 2: Vertical Resize-Grip + localStorage

CSS `resize: vertical` auf einem Wrapper-Div um den iframe. ResizeObserver triggert `localStorage.setItem('cm:incoming:pdfHeight', height)`. Beim Mount wird der gespeicherte Wert geladen und als `style.height` gesetzt; falls nicht vorhanden, fällt auf `min-h-[70vh]` zurück.

Achtung: iframe selbst kann CSS `resize` nicht; deshalb braucht es den Wrapper-Div mit `overflow: hidden` + `resize: vertical`.

### Decision 3: Sheet-Breite `sm:max-w-3xl` (768px)

96px breiter als heute. Form bleibt zwei-spaltig, PDF gewinnt 96px horizontal — was bei A4-Hochformat (genau 794px Breite bei 96 DPI) den Unterschied macht zwischen "scrollen müssen" und "auf einmal sehen".

### Decision 4: Persistierung pro User, nicht pro Tenant

`localStorage`-Key `cm:incoming:pdfHeight`. User-Setting unnötig — Höhe ist sehr persönliche Präferenz, abhängig von Bildschirm.

## Risks / Trade-offs

- **[Risk]** Sheet wird breiter als der Viewport auf kleinen Notebooks → horizontaler Scrollbar
  → **Mitigation**: Shadcn-Sheet hat schon `responsive`-Verhalten via `sm:max-w-3xl` — auf <640px Screens fällt es auf `w-full` zurück.
- **[Trade-off]** Resize-Grip nicht offensichtlich. Lösung: kleines `GripHorizontal`-Icon visuell andeuten, mit Tooltip.

## Migration Plan

Reine CSS-Änderung. Kein Migrations-Risiko.

## Open Questions

- Keine.
