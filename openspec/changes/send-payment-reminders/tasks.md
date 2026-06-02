## 1. Backend — Datenmodell & Migrationen

- [x] 1.1 `PaymentReminder(TenantModel)` in `apps/invoices/models.py` anlegen: FK `invoice_record`, `stage` (0–3), `language`, `title`, `subject`, `body_text`, `fee_amount`, `interest_amount`, `interest_rate_snapshot`, `interest_days`, `pdf_file`, `sent_at`, `sent_to` (JSON), `created_by`
- [x] 1.2 Feld `due_date` (DateField, nullable) zu `InvoiceRecord` hinzufügen
- [x] 1.3 Feld `payment_term_days` (PositiveInteger, nullable) zu `Customer` hinzufügen
- [x] 1.4 Feld `payment_term_days` (PositiveInteger, nullable) zu `Contract` hinzufügen
- [x] 1.5 Schema-Migration für 1.1–1.4 erzeugen (`make makemigrations`)
- [x] 1.6 Daten-Migration: `due_date` für Bestandsrechnungen aus `invoice_date + globaler Default` backfillen
- [x] 1.7 Migrationen ausführen und prüfen (`make migrate`)

## 2. Backend — Permissions

- [x] 2.1 Ressource `reminders` mit Aktionen `send`, `settings` in `PERMISSION_REGISTRY` (`apps/core/permissions.py`) ergänzen
- [x] 2.2 Default-Rollen-Seeding aktualisieren: Admin = `send`+`settings`, Manager = `send`, Viewer = keine
- [x] 2.3 Management-Command/Daten-Migration, um bestehende DB-Rollen um die neuen Permissions zu ergänzen
- [x] 2.4 Test: `reminders.send` / `reminders.settings` greifen korrekt in `has_perm_check`

## 3. Backend — Zahlungsziel & Verzugsberechnung

- [x] 3.1 Auflösungsfunktion `resolve_payment_term(contract, customer, tenant)` (Vertrag → Kunde → globaler Default)
- [x] 3.2 `due_date` bei Rechnungserstellung aus aufgelöstem Zahlungsziel + `invoice_date` setzen
- [x] 3.3 Property/Methode `overdue_days` auf `InvoiceRecord`: `max(0, today − due_date)`, 0 wenn bezahlt oder nicht fällig
- [x] 3.4 Test: Auflösungs-Hierarchie und `overdue_days` (bezahlt, nicht fällig, überfällig)

## 4. Backend — Settings & Vorlagen

- [x] 4.1 Defaults und Lese-/Schreiblogik für `tenant.settings["dunning"]` (`default_payment_term_days`, `overdue_red_threshold_days`, `mahnfaehig_threshold_days`, `interest_rate`, `default_fee_per_stage`)
- [x] 4.2 Eingebaute Standard-Mahnvorlagen DE/EN für Stufen 0–3 (`title`, `subject`, `body`)
- [x] 4.3 `_get_dunning_template(tenant, lang, stage)` mit Fallback auf Standardvorlage
- [x] 4.4 Mahnfähigkeits-Logik: Rechnung mahnfähig, wenn unbezahlt, nicht voided, `overdue_days >= mahnfaehig_threshold_days`
- [x] 4.5 Vorberechnung `fee` und `interest` (`total_gross × interest_rate/100 × interest_days/365`)
- [x] 4.6 Test: Vorlagen-Fallback, Mahnfähigkeit, Gebühr-/Zinsberechnung

## 5. Backend — Mahn-PDF

- [x] 5.1 HTML-Template `apps/invoices/templates/invoices/dunning.html` (Stufentitel als Überschrift, Rechnungsbezug, Gebühr/Zinsen, Mahntext)
- [x] 5.2 Methode `generate_dunning_pdf(reminder)` in `InvoiceService`, wiederverwendet `_get_template_context()`
- [x] 5.3 PDF in Object Storage ablegen und auf `PaymentReminder.pdf_file` referenzieren
- [x] 5.4 Test: PDF-Generierung für eine Stufe-1-Mahnung

## 6. Backend — E-Mail-Versand

- [x] 6.1 Standard-E-Mail-Templates und `tenant.settings["dunning_email_templates"][lang][stage]` mit Fallback
- [x] 6.2 BCC-Schlüssel `"dunning"` in `get_document_bcc` unterstützen
- [x] 6.3 Celery-Task `send_dunning_email_task`: PDF anhängen, via `m365.send_mail()` versenden
- [x] 6.4 `sent_at`/`sent_to` erst nach erfolgreichem Versand setzen; Fehler lassen Mahnung erneut auslösbar
- [x] 6.5 Test: Versand-Task (Erfolg + Fehlerfall)

## 7. Backend — Status & Audit

- [x] 7.1 Rechnungsstatus auf `DUNNING` setzen, wenn erste Mahnung erfolgreich versendet
- [x] 7.2 Im Pfad der Zahlungszuordnung (`InvoicePaymentMatch`-Erstellung): Status auf `PAID` setzen, sobald Rechnung voll bezahlt (bereits durch `create_payment_match_for_record` abgedeckt — deckt `DUNNING` ab)
- [x] 7.3 Audit-Helfer `log_reminder_sent` in `apps/invoices/audit.py`
- [x] 7.4 Test: Statuswechsel DUNNING→PAID, Audit-Eintrag bei Versand

## 8. Backend — GraphQL-Schema

- [x] 8.1 Type `PaymentReminderType` in `apps/invoices/dunning_schema.py`
- [x] 8.2 `InvoiceRecordType` um Felder `dueDate`, `overdueDays` und Resolver `paymentReminders` erweitern
- [x] 8.3 `CustomerType`/`ContractType` um `paymentTermDays` und Resolver `paymentReminders` erweitern (lazy types)
- [x] 8.4 `paymentTermDays` in Vertrags-Write-Mutationen + dedizierte `updateCustomerPaymentTerm`-Mutation
- [x] 8.5 Query `dunningSettings`; Mutationen `createPaymentReminder` (vorbefüllter Entwurf), `sendPaymentReminder`, `saveDunningSettings` mit `check_perm` und Result-Type
- [x] 8.6 `sendPaymentReminder`: Re-Check `is_paid` unmittelbar vor Versand
- [x] 8.7 Test: Mutationen mit/ohne Permission, Versand-Block bei bezahlter Rechnung

## 9. Frontend — Verzugsspalte

- [x] 9.1 Spalte „Verzug" (Verzugstage) in alle Rechnungsübersichts-Tabellen einfügen
- [x] 9.2 Spalte sortierbar machen (bestehendes Sortable-Header-Pattern)
- [x] 9.3 Roter Wert ab `overdue_red_threshold_days` (Schwelle aus `dunningSettings`)
- [x] 9.4 `data-testid` für Verzugsspalte/-zelle vergeben

## 10. Frontend — Mahn-Auslöser

- [x] 10.1 Mahnfähige Rechnungen in Rechnungsübersicht/Kundenansicht kennzeichnen, Aktion „Mahnen" (nur mit `reminders.send`)
- [x] 10.2 Auslöse-Dialog: Stufenauswahl (vorgeschlagen + überschreibbar), Vorschau Titel/Betreff/Text, editierbar
- [x] 10.3 Toggles für Mahngebühr und Verzugszinsen mit vorberechneten Beträgen
- [x] 10.4 `sendPaymentReminder` aufrufen, Erfolg/Fehler anzeigen
- [x] 10.5 `data-testid` für Dialog und Steuerelemente

## 11. Frontend — Mahnungs-Anzeige

- [x] 11.1 Versendete Mahnungen im Rechnungsverlauf der Rechnungsdetailansicht anzeigen (Stufe, Versandzeitpunkt, PDF-Link)
- [x] 11.2 Mahnungen in Kunden- und Vertragsansicht anzeigen inkl. zugeordneter Rechnung
- [x] 11.3 `data-testid` für Mahnungs-Listen/-Einträge

## 12. Frontend — Mahn-Einstellungen

- [x] 12.1 Settings-Sektion „Mahnwesen" (nur mit `reminders.settings`): Vorlagen DE/EN je Stufe (Titel/Betreff/Text), Zinssatz, Gebühren je Stufe, globaler Zahlungsziel-Default, Schwellwerte
- [x] 12.2 Feld `payment_term_days` in Kunden- und Vertragsformular
- [x] 12.3 `saveDunningSettings` anbinden
- [x] 12.4 Settings-Sektion zu `searchablePages` in `Sidebar.tsx` hinzufügen

## 13. i18n

- [x] 13.1 Deutsche und englische Übersetzungen für Mahn-UI, Verzugsspalte und Settings-Sektion ergänzen

## 14. Tests & Abschluss

- [x] 14.1 E2E-Test (Playwright): Mahnung aus Rechnungsübersicht erstellen und versenden — `setup_test_data` legt jetzt eine 30-Tage-überfällige Fixture-Rechnung `E2E-OVERDUE-0001` an
- [x] 14.2 E2E-Test: Verzugsspalte sichtbar + sortierbar (`payment-reminders.spec.ts`) — rote Hervorhebung folgt mit Test-Fixture
- [x] 14.3 E2E-Test: Mahnungs-Sektion (Empty-State) in Kunden-/Vertrags-/Rechnungs-Detail
- [x] 14.4 `make test-back` und Frontend-Typecheck (`npx tsc --noEmit`) grün

## 15. Tests — Frontend Component (nachgezogen)

- [x] 15.1 `PaymentReminderList.test.tsx` — Empty-State, Reminder-Row, PDF-Link, Sortierung, Invoice-Link
- [x] 15.2 `ReminderDialog.test.tsx` — Draft laden, Fehler-State, Send-Erfolg mit Mutation-Variablen, Send-Fehler hält Dialog offen
