## Context

Contract Manager erkennt offene Rechnungen über `InvoiceRecord.is_paid` (prüft `payment_matches.exists()` aus dem Bank-Matching). Es fehlt jeder Mahnprozess. Relevante vorhandene Infrastruktur:

- **Rechnung**: `apps/invoices/models.py` — `InvoiceRecord` mit `invoice_date`, `total_gross`, `status`. Die `status`-Choices enthalten bereits `DUNNING`. Kein `due_date`-Feld vorhanden.
- **PDF**: WeasyPrint, HTML-Templates unter `apps/invoices/templates/invoices/`, Einstieg `InvoiceService.generate_pdf_for_record()`. Template-Kontext zieht `CompanyLegalData` und `InvoiceTemplate` (Logo, Akzentfarbe).
- **E-Mail**: M365 Graph API `apps/core/m365.py:send_mail()`, BCC via `tenant.settings["document_email_bcc"]`. Versand asynchron als Celery-Task. E-Mail-Templates pro Sprache in `tenant.settings["invoice_email_templates"]`, Pattern `_get_email_template()`.
- **RBAC**: `PERMISSION_REGISTRY` in `apps/core/permissions.py`; `check_perm`/`require_perm`.
- **Settings**: `Tenant.settings` JSONField.
- **GraphQL**: `apps/invoices/schema.py` — `InvoiceQuery` / `InvoiceMutation`, Result-Type-Pattern.
- **Audit**: `AuditLog` + manuelle Helfer in `apps/invoices/audit.py`.

Constraint: keine Bündelung — eine Mahnung gehört zu genau einer Rechnung (vgl. proposal.md).

## Goals / Non-Goals

**Goals:**

- Mehrstufiges Mahnen (1./2./3. Mahnung) pro Rechnung, manuell ausgelöst.
- Konfigurierbare Vorlagen DE/EN je Stufe; Text vor Versand editierbar.
- Verzugszinsen + Mahngebühren konfigurierbar, pro Mahnung an-/abwählbar.
- Mahn-PDF generieren und per E-Mail versenden.
- Verzugsspalte (Tage) in allen Rechnungsübersichten, rot ab Schwellwert.
- Mahnungen sichtbar in Rechnungsverlauf, Kunden- und Vertragsansicht inkl. Rechnungs-Zuordnung.
- Zwei neue Permissions: Mahnen, Mahn-Einstellungen.

**Non-Goals:**

- Keine automatische/zeitgesteuerte Mahnerzeugung — Auslösung bleibt manuell.
- Keine Bündelung mehrerer Rechnungen in einer Mahnung.
- Kein Inkasso-/Klage-Workflow nach der 3. Mahnung.
- Keine kundenindividuellen Zinssätze — Konfiguration gilt tenant-weit.

## Decisions

### D1 — Modell: `PaymentReminder` in `apps/invoices`

Neues Model `PaymentReminder(TenantModel)` mit FK `invoice_record` (1:N — eine Rechnung kann mehrere Mahnungen über Stufen hinweg haben). Felder: `stage` (1–3), `language` (de/en), `subject`, `body_text` (finaler editierter Text), `fee_amount`, `interest_amount`, `interest_rate_snapshot`, `interest_days`, `pdf_file`, `sent_at`, `sent_to` (JSON-Liste), `created_by`.

Alternative verworfen: eigene App `apps/dunning`. Mahnung ist eng an Rechnung gekoppelt (PDF-Service, Audit, Schema teilen sich Code) → gleiche App reduziert Cross-App-Imports und zirkuläre GraphQL-Lazy-Types.

### D2 — Verzugsberechnung: `due_date` + Zahlungsziel-Hierarchie

Recherche bestätigt: weder `Contract`, `Customer` noch `InvoiceRecord` besitzen ein Zahlungsziel-Feld. Daher dreistufige Hierarchie:

- **Global**: `tenant.settings["dunning"]["default_payment_term_days"]` (z. B. 14).
- **Pro Kunde**: neues Feld `Customer.payment_term_days` (nullable PositiveInteger; leer → global).
- **Pro Vertrag**: neues Feld `Contract.payment_term_days` (nullable; leer → Kunde → global).

Auflösung bei Rechnungserstellung: `contract → customer → global`. Neues Feld `due_date` (DateField, nullable) auf `InvoiceRecord` wird auf `invoice_date + aufgelöstes Zahlungsziel` gesetzt. `overdue_days = max(0, today − due_date)` wenn nicht bezahlt, sonst 0.

Alternative verworfen: Verzug on-the-fly ohne gespeichertes `due_date` — bricht bei abweichenden Zahlungszielen je Rechnung und macht Filter/Sortierung in SQL teuer.

Bestandsrechnungen: Backfill-Migration setzt `due_date = invoice_date + globaler Default` (keine rückwirkende Kunden-/Vertrags-Auflösung).

### D3 — Permissions: neue Ressource `reminders`

`PERMISSION_REGISTRY` erhält `"reminders": ["send", "settings"]`:

- `reminders.send` — Mahnung erstellen/versenden.
- `reminders.settings` — Vorlagen, Zinssatz, Gebühren, Schwellwerte konfigurieren.
- Mahnungen **ansehen** nutzt vorhandenes `invoices.read` — keine neue Permission.

Default-Rollen: Admin erhält beide; Manager erhält `reminders.send`, nicht `reminders.settings` (analog `invoices.settings`); Viewer keine.

Alternative verworfen: Aktionen unter `invoices` (`send_reminders`, `reminder_settings`) — eigene Ressource bildet die UI-Sektion sauber ab und passt zur Vorgabe „eigene Permission".

### D4 — Mehrstufigkeit, Stufe 0 = Zahlungserinnerung

Vier Stufen `0–3`: Stufe 0 = (zinsfreie) Zahlungserinnerung, Stufen 1–3 = 1./2./3. Mahnung. Der **Anzeige-/PDF-Titel jeder Stufe ist Teil der Vorlage**, nicht hartkodiert — so bleibt die Bezeichnung flexibel (z. B. „Zahlungserinnerung", „Freundliche Erinnerung", „Letzte Mahnung"). Jede Vorlage je Sprache und Stufe besteht aus `title`, `subject`, `body`.

Vorgeschlagene nächste Stufe je Rechnung = `max(stage vorhandener Mahnungen) + 1`, Beginn bei 0, hart begrenzt auf 3. Stufe bleibt im Auslöse-Dialog überschreibbar. Eskalations-Tracking ergibt sich aus den `PaymentReminder`-Zeilen der Rechnung — kein Zähler-Feld auf der Rechnung nötig. Stufe 0 schlägt standardmäßig keine Verzugszinsen vor (Gebühr/Zinsen bleiben dennoch per Toggle aktivierbar).

### D5 — Gebühren & Zinsen als Snapshot

Settings halten `default_fee_per_stage` (Betrag je Stufe) und `interest_rate` (Jahres-%). Im Auslöse-Dialog werden Gebühr und Zinsen vorberechnet angezeigt, einzeln per Toggle abwählbar. Die tatsächlich verwendeten Werte werden als Snapshot auf `PaymentReminder` gespeichert (`fee_amount`, `interest_amount`, `interest_rate_snapshot`, `interest_days`), damit spätere Settings-Änderungen historische Mahnungen nicht verfälschen.

Zinsberechnung: `interest = total_gross × interest_rate/100 × interest_days/365`, `interest_days` = Verzugstage zum Mahndatum. Zinssatz wird als fertiger Prozentwert konfiguriert (kein automatisches Nachziehen des BGB-Basiszinssatzes — siehe Open Questions).

### D6 — Mahn-PDF

Neues Template `apps/invoices/templates/invoices/dunning.html`. Neue Service-Methode `generate_dunning_pdf(reminder)` analog `generate_pdf_for_record()`, wiederverwendet `_get_template_context()` (Logo, Akzentfarbe, Firmen-Rechtsdaten). PDF wird in Object Storage abgelegt und auf `PaymentReminder.pdf_file` referenziert.

### D7 — E-Mail-Versand

Wiederverwendung von `m365.send_mail()` mit Mahn-PDF als Anhang. Templates pro Sprache **und Stufe** in `tenant.settings["dunning_email_templates"][lang][stage]` (Keys `subject`, `body`); Fallback auf hartkodierte Defaults via `_get_dunning_email_template()`. BCC über bestehendes `document_email_bcc` mit neuem Schlüssel `"dunning"`. Versand als Celery-Task `send_dunning_email_task`, Statusrückschreibung in `PaymentReminder.sent_at`/`sent_to`.

### D8 — Rechnungsstatus

Beim Versand der ersten Mahnung wird `InvoiceRecord.status` auf `DUNNING` gesetzt (Choice existiert bereits). Folgemahnungen ändern den Status nicht weiter. `is_paid` bleibt unabhängig; eine bezahlte Rechnung (`is_paid == True`) ist nicht mehr mahnfähig — der Auslöser blendet sie aus bzw. blockt die Mutation.

Rücksetzung: Im Pfad der Zahlungszuordnung — sobald ein `InvoicePaymentMatch` angelegt wird und die Rechnung dadurch voll bezahlt ist (`is_paid == True`) — wird `status` auf `PAID` gesetzt. Das setzt `DUNNING` automatisch zurück, ohne separaten Trigger.

### D9 — Settings-Ablage

Alle Mahn-Settings unter `tenant.settings`:
`dunning` → `{ default_payment_term_days, overdue_red_threshold_days, mahnfaehig_threshold_days, interest_rate, default_fee_per_stage: {0,1,2,3} }`;
`dunning_email_templates` → `{ de: {0,1,2,3}, en: {0,1,2,3} }`, jede Stufe `{ title, subject, body }`.

### D10 — GraphQL-Oberfläche

- `InvoiceType`: neue Felder `dueDate`, `overdueDays`, Resolver `paymentReminders: [PaymentReminderType]`.
- `CustomerType` / `ContractType`: neues Feld `paymentTermDays` (Schreibzugriff via bestehende write-Mutationen), Resolver `paymentReminders` (lazy types, vgl. CLAUDE.md).
- Neuer Type `PaymentReminderType`, Query `dunningSettings`, Mutationen `createPaymentReminder` (liefert vorbefüllten Entwurf inkl. berechneter Gebühr/Zinsen), `sendPaymentReminder`, `saveDunningSettings` — alle mit Result-Type-Pattern und `check_perm`.

## Risks / Trade-offs

- **`due_date`-Backfill ungenau** → Migration nutzt einheitlichen Default; Settings-Tab erlaubt späteres Korrigieren des Defaults; einzelne Rechnungen sind im UI nachpflegbar.
- **Zinsberechnung rechtlich heikel** (BGB-Basiszinssatz ändert sich halbjährlich, B2B +9 / Verbraucher +5 Prozentpunkte) → bewusst nur fester konfigurierbarer Prozentsatz + manueller Abwahl-Toggle; keine automatische Rechtsberechnung. Verantwortung beim User.
- **Mahnung trotz zwischenzeitlicher Zahlung** (Bank-Import läuft asynchron) → `is_paid`-Check unmittelbar vor `sendPaymentReminder`; PDF-Generierung und Versand erst nach Re-Check.
- **PDF-/E-Mail-Fehler im Celery-Task** → `PaymentReminder` wird erst nach erfolgreichem Versand als `sent` markiert; fehlgeschlagene Tasks bleiben re-triggerbar; Audit-Log nur bei Erfolg.
- **Verzugsspalte in vielen Tabellen** → `overdueDays` zentral als Feld auf `InvoiceType`, alle Übersichten konsumieren dasselbe Feld; rote Schwelle rein im Frontend ausgewertet.

## Migration Plan

1. Migration: `PaymentReminder`-Model, `InvoiceRecord.due_date`, `Customer.payment_term_days`, `Contract.payment_term_days`.
2. Daten-Migration: `due_date` für Bestandsrechnungen aus `invoice_date + globaler Default` backfillen.
3. `PERMISSION_REGISTRY` um `reminders` erweitern; Default-Rollen-Seeding aktualisieren; Hinweis: bestehende, in der DB gespeicherte Rollen ggf. per Daten-Migration/Management-Command um die neuen Permissions ergänzen.
4. Default-Werte für `tenant.settings["dunning"]` lazy beim ersten Settings-Zugriff (kein Migrationszwang auf JSONField).
5. Frontend-Rollout: Verzugsspalte und Mahn-UI hinter vorhandenem Permission-Gating — keine Feature-Flag nötig.

Rollback: Mahn-UI ist additiv; bei Rollback Models per Reverse-Migration entfernbar, `due_date` kann bestehen bleiben (schadlos).

## Open Questions

- BGB-Basiszinssatz automatisch nachziehen: bewusst zurückgestellt (keine Priorität). Bleibt vorerst fester konfigurierbarer Prozentsatz; spätere Erweiterung möglich.
- Stufen-Obergrenze: Modell erlaubt 0–3. Falls in der Praxis mehr als drei Mahnungen nötig sind, muss die Begrenzung angehoben werden — vorerst auf 3 fixiert.
