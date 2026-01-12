# Contract-Manager

Für eine kleine Firma (20-30 MA) mit 70-150 Kunden soll der Contract Manager ein Tool zur Vertragsverwaltung sein.

## Fakten

### Kunden
- Kunden werden aus Hubspot synchronisiert (nur inbound, one-way, read-only)
- Sync: Initial-Import + Webhook (Fallback: regelmäßiger Sync)
- Daten aus Hubspot: Firmenname (Pflicht), Adresse (optional)
- Lokales Notizfeld pro Kunde (nur im Contract-Manager)
- Kunden können mehrere Verträge haben (unabhängig oder miteinander verbunden)
- Ein Standort pro Kunde (keine Konzernstrukturen)
- Kein Löschen: Deaktivierte Hubspot-Kunden werden markiert, Verträge bleiben erhalten

### Produkte

**Herkunft & Sync:**
- Import aus Hubspot (komplett, read-only, Sync wie Kunden)
- Eigene Produkte manuell anlegbar (z.B. Legacy-Produkte)
- Gelöschte Hubspot-Produkte bleiben markiert im System

**Struktur:**
- Primär Subscriptions, One-off optional für Vollständigkeit
- Kategorien/Gruppen optional
- Produktvarianten optional (z.B. S/M/L)
- Abhängigkeiten definierbar:
  - Automatisch mitgebucht (Pflicht)
  - Hinweis bei Auswahl (Empfehlung)

**Preise:**
- Preise aus CRM, für eigene Produkte manuell festlegbar
- I.d.R. Stückpreis, aber alle Modelle möglich (Staffel, pro Einheit)
- Kundenspezifische Preislisten möglich
- Kundenspezifische Preise via Rabatt oder direkter Preisänderung pro Kunde/Vertrag

**Lifecycle:**
- Produkte können deaktiviert werden (nicht mehr buchbar, aber in bestehenden Verträgen)
- Optionaler Nachfolger definierbar

### Verträge

**Lebenszyklus:**
- Status: Entwurf → Aktiv → (Pausiert: alles eingefroren) → Gekündigt → Beendet
- Vertrag startet ab definiertem Startdatum
- Kündigung beidseitig möglich (Kunde oder Anbieter)
- Kündigungsfristen frei verhandelbar (z.B. Mindestlaufzeit 12 Mo, dann 3 Mo zum Laufzeitende, danach 3 Mo zum Monatsende)

**Laufzeiten:**
- Regelfall: Unbefristete Subscriptions mit Mindestlaufzeit
- Ausnahme: Befristete Verträge (enden automatisch)

**Preisanpassungen:**
- Automatische Inflationsanpassung (z.B. jährlich zum 1.1.)
- Manuelle Preisanpassungen zu beliebigen Daten (auch mehrfach für die Zukunft, z.B. 1.7.26, 1.1.27, 1.1.28)

**Struktur:**
- Verträge enthalten n Produkte in Anzahl m
- Verträge haben Komplettpreis oder Produkt-Einzelpreise
- Primär-/Sekundärverträge: Sekundär fügt Produkte hinzu mit eigenem Startdatum für Abrechnung
- Änderungen/Nachträge sind die Regel (keine Neuverträge nötig)

**Dokumente:**
- Upload von n Dokumenten pro Vertrag oder Kunde (PDFs, Scans)

### Preise & Abrechnung

**Währung:**
- Eine Währung pro System, wählbar (Default: EUR)

**Abrechnungszyklus:**
- Intervalle: monatlich, quartalsweise, halbjährlich, jährlich
- Stichtag pro Vertrag individuell (Default: Abrechnungsintervall-Anfang)
- Startdatum und Abrechnungsbeginn können unterschiedlich sein (Bruchteilpreis möglich)
- Subscriptions im Voraus, nutzungsbasiert nachträglich

**Preisberechnung:**
- Pro-rata oder frei wählbarer Preis bei Vertragsstart
- Kündigung i.d.R. zum Abrechnungsintervall-Ende
- Mengenänderungen (Up-/Downgrade): flexibel, immer abfragen

**Rechnungsstellung:**
- Contract-Manager erstellt keine Rechnungen
- Dient als Datengrundlage, Export und Kontrolle
- API zu Rechnungstools später

**Preishistorie:**
- Vollständige Nachvollziehbarkeit: Welcher Preis galt wann und warum
- Rückwirkende Auswertungen möglich

### Rabatte & Konditionen

**Rabattarten:**
- Prozentual (z.B. 10%)
- Absolutbetrag (z.B. 50€)
- Staffelrabatt (ab Menge X: Y%)
- Gratiseinheiten (z.B. 12 zahlen, 1 gratis)

**Bezug:**
- Auf einzelnes Produkt (Line Item)
- Auf gesamten Vertrag
- Auf Produktkategorie
- Auf Preisliste

**Gültigkeit:**
- Permanent (gesamte Vertragslaufzeit)
- Befristet (z.B. nur erstes Jahr)
- Einmalig (nur erste Rechnung)

**Kombinationen:**
- Mehrere Rabatte gleichzeitig möglich
- Reihenfolge: erst Line-Item-Rabatt, dann Vertrags-Rabatt

**Kundenvereinbarungen:**
- Gelten automatisch für alle Verträge des Kunden
- Können pro Vertrag deaktiviert oder überschrieben werden

**Sonstiges:**
- Zahlungsziele etc. nicht relevant, ggf. in Notizen

### Preisanpassungen

**Preisquellen (Hierarchie):**
1. Vertraglich fixierter Preis (höchste Priorität)
2. Kundenspezifische Preisliste
3. Standard-Listenpreis (aus CRM)

**Automatische Anpassungen:**
- System-Default: Inflationsanpassung (z.B. X% zum 1.1.)
- Kann pro Kunde/Vertrag überschrieben werden
- Auch zeitlich begrenzt möglich (z.B. "keine Erhöhung für 3 Jahre")

**Preislistenanpassungen aus CRM:**
- Wirken für alle Kunden ab nächster Verlängerung
- Außer: vertraglich anderes vereinbart

**Typische Szenarien:**
- Fixpreis für Jahr 1, 2, 3 → danach Preis Jahr 3 + Inflation
- Fixpreis für 24 Monate → danach Listenpreis
- Immer Listenpreis minus X%
- Keine automatischen Erhöhungen
- Viele weitere Kombinationen möglich

**Priorität bei Konflikten:**
Kundenvereinbarung > Vertragsklausel > System-Default

**Erinnerungen:**
- Konfigurierbare Ankündigungen (z.B. "Vertragsende in 3 Monaten", "Preiserhöhung in 30 Tagen")

### Auditing
- Vollständiges Audit-Log für alle Änderungen im System
- Erfasst: Wer, Was, Wann, Alter Wert, Neuer Wert
- Gilt für: Kunden, Verträge, Produkte, Konditionen, etc.

### Benutzer & Berechtigungen

**Multi-Tenant:**
- System ist mandantenfähig (mehrere Unternehmen)
- 2-20 Benutzer pro Tenant
- Strikte Datentrennung zwischen Tenants

**Benutzerkreis:**
- Primär intern (Vertrieb, Buchhaltung, GF)
- Später evtl. externe (Steuerberater, Buchprüfer)

**Rollen & Rechte:**
- Rollen mit Defaults, konfigurierbar
- Zunächst: App-Admin (Hersteller) legt Rollen an, Tenants weisen nur zu
- Später: Tenants können eigene Rollen konfigurieren
- Einschränkbar: Kunden, Verträge, Produkte, Preise, Rabatte, Audit-Log, Einstellungen

**Datensichtbarkeit:**
- Default: alle Benutzer sehen alle Daten (innerhalb ihres Tenants)
- Später einschränkbar (z.B. nach Team/Region)

**Freigabe-Workflows:**
- Zunächst nicht nötig
- Neue Deals kommen aus CRM (Hubspot)

**Authentifizierung:**
- Phase 1: User/Passwort
- Phase 2: Magic Email Link / Email-Code
- Später optional: SSO (Google Workspace, Microsoft 365)

### Output & Integration

**Reporting & Auswertungen:**
- Umsatz pro Kunde/Zeitraum
- MRR / ARR (Monthly/Annual Recurring Revenue)
- Auslaufende Verträge (in X Tagen)
- Kündigungen / Churn-Rate
- Rabattübersicht
- Produkt-Mix (was wird wie oft verkauft)

**Dashboards:**
- Übersicht auf Startseite mit wichtigen KPIs

**Export:**
- Excel/CSV für alle relevanten Daten
- PDF-Reports (Vertragsübersichten)

**Dokumente:**
- Upload externer Dokumente ✓
- PDF-Generierung für Vertragsübersichten

**Integrationen:**
- Hubspot: Kunden-Sync, Produkt-Sync (inbound)
- Buchhaltung/ERP: zunächst nicht nötig
- Rechnungsstellung: generischer Export, später Integration

**Benachrichtigungen:**
- E-Mail (definitiv)
- Optional: Kalender, Teams, Slack

**API:**
- Eigene API bereitstellen (wichtig!)
- Webhooks bei Ereignissen (Vertrag erstellt, Kündigung, Preisänderung, etc.)
- Für externe Systeme nutzbar

### Sonstiges
- Das Tool wird nur intern genutzt (pro Tenant)
- Später evtl. Öffnung für externe Prüfer

## Tech Stack
- React with Typescript
- Django with Strawberry-GraphQL https://github.com/strawberry-graphql/strawberry-django to use GraphQL to interact between front-backend
- PostgreSQL as a database
- if needed, Redis for caching

## Architektur-Entscheidungen

| Thema | Entscheidung | Begründung |
|-------|--------------|------------|
| Multi-Tenant | Shared Schema + Tenant-ID | Einfach, ausreichend für 70-150 Tenants |
| Temporale Daten | Validity Columns (valid_from, valid_to) | Einfache "Was galt wann?"-Abfragen |
| Audit-Log | Application Level (django-auditlog) | Flexibel, testbar |
| Vertrags-Versionierung | Amendments | Bildet reale Nachträge ab, separat unterschrieben |
| Preisberechnung | Hybrid | Basis materialisiert, Modifikationen zur Laufzeit |

## Datenmodell (Entwurf)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TENANT & AUTH                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tenant                      User                                           │
│  ├── id (PK)                 ├── id (PK)                                    │
│  ├── name                    ├── tenant_id (FK)                             │
│  ├── currency (EUR)          ├── email                                      │
│  ├── hubspot_config          ├── role_id (FK)                               │
│  └── settings (JSON)         └── is_active                                  │
│                                                                             │
│  Role                        AuditLog                                       │
│  ├── id (PK)                 ├── id (PK)                                    │
│  ├── tenant_id (FK)          ├── tenant_id (FK)                             │
│  ├── name                    ├── user_id (FK)                               │
│  └── permissions (JSON)      ├── action (create/update/delete)              │
│                              ├── model_name                                 │
│                              ├── object_id                                  │
│                              ├── old_values (JSON)                          │
│                              ├── new_values (JSON)                          │
│                              └── timestamp                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ KUNDEN                                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Customer                    CustomerNote                                   │
│  ├── id (PK)                 ├── id (PK)                                    │
│  ├── tenant_id (FK)          ├── customer_id (FK)                           │
│  ├── hubspot_id (unique)     ├── user_id (FK)                               │
│  ├── name                    ├── content                                    │
│  ├── address (JSON)          └── created_at                                 │
│  ├── is_active                                                              │
│  ├── synced_at               CustomerAgreement                              │
│  └── hubspot_deleted_at      ├── id (PK)                                    │
│                              ├── customer_id (FK)                           │
│                              ├── type (discount_percent, custom_pricelist)  │
│                              ├── value (JSON)                               │
│                              ├── valid_from                                 │
│                              └── valid_to (nullable)                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PRODUKTE                                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Product                     ProductPrice                                   │
│  ├── id (PK)                 ├── id (PK)                                    │
│  ├── tenant_id (FK)          ├── product_id (FK)                            │
│  ├── hubspot_id (nullable)   ├── price                                      │
│  ├── sku                     ├── price_model (unit, tiered, per_unit)       │
│  ├── name                    ├── tiers (JSON, nullable)                     │
│  ├── description             ├── valid_from                                 │
│  ├── category_id (FK)        └── valid_to (nullable)                        │
│  ├── type (subscription, one_off)                                           │
│  ├── is_active               ProductDependency                              │
│  ├── successor_id (FK, nullable)  ├── id (PK)                               │
│  └── hubspot_deleted_at      ├── product_id (FK)                            │
│                              ├── requires_product_id (FK)                   │
│  ProductCategory             └── type (required, recommended)               │
│  ├── id (PK)                                                                │
│  ├── tenant_id (FK)          PriceList                                      │
│  └── name                    ├── id (PK)                                    │
│                              ├── tenant_id (FK)                             │
│  ProductVariant              ├── name                                       │
│  ├── id (PK)                 └── is_default                                 │
│  ├── product_id (FK)                                                        │
│  ├── name (S/M/L)            PriceListItem                                  │
│  └── price_modifier          ├── id (PK)                                    │
│                              ├── pricelist_id (FK)                          │
│                              ├── product_id (FK)                            │
│                              ├── price                                      │
│                              ├── valid_from                                 │
│                              └── valid_to (nullable)                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ VERTRÄGE                                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Contract                                                                   │
│  ├── id (PK)                                                                │
│  ├── tenant_id (FK)                                                         │
│  ├── customer_id (FK)                                                       │
│  ├── primary_contract_id (FK, nullable) -- für Sekundärverträge             │
│  ├── status (draft, active, paused, cancelled, ended)                       │
│  ├── start_date                                                             │
│  ├── end_date (nullable) -- nur bei befristeten                             │
│  ├── billing_start_date                                                     │
│  ├── billing_interval (monthly, quarterly, semi_annual, annual)             │
│  ├── billing_anchor_day                                                     │
│  ├── min_duration_months (nullable)                                         │
│  ├── notice_period_months                                                   │
│  ├── notice_period_anchor (end_of_duration, end_of_month, end_of_quarter)   │
│  ├── cancelled_at (nullable)                                                │
│  ├── cancellation_effective_date (nullable)                                 │
│  └── created_at                                                             │
│                                                                             │
│  ContractItem                                                               │
│  ├── id (PK)                                                                │
│  ├── contract_id (FK)                                                       │
│  ├── product_id (FK)                                                        │
│  ├── variant_id (FK, nullable)                                              │
│  ├── quantity                                                               │
│  ├── unit_price -- materialisierter Preis bei Vertragsschluss               │
│  ├── price_source (list, custom, customer_agreement)                        │
│  └── added_by_amendment_id (FK, nullable)                                   │
│                                                                             │
│  ContractAmendment                                                          │
│  ├── id (PK)                                                                │
│  ├── contract_id (FK)                                                       │
│  ├── effective_date                                                         │
│  ├── type (product_added, product_removed, quantity_changed,                │
│  │         price_changed, terms_changed)                                    │
│  ├── description                                                            │
│  ├── changes (JSON) -- Details der Änderung                                 │
│  └── created_at                                                             │
│                                                                             │
│  ContractDocument                                                           │
│  ├── id (PK)                                                                │
│  ├── contract_id (FK, nullable)                                             │
│  ├── customer_id (FK, nullable) -- oder auf Kundenebene                     │
│  ├── filename                                                               │
│  ├── file_path                                                              │
│  ├── uploaded_by_id (FK)                                                    │
│  └── uploaded_at                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ RABATTE & PREISANPASSUNGEN                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Discount                                                                   │
│  ├── id (PK)                                                                │
│  ├── tenant_id (FK)                                                         │
│  ├── contract_id (FK, nullable) -- Vertragsrabatt                           │
│  ├── contract_item_id (FK, nullable) -- Line-Item-Rabatt                    │
│  ├── customer_id (FK, nullable) -- Kundenrabatt                             │
│  ├── type (percent, absolute, tiered, free_units)                           │
│  ├── value (JSON) -- abhängig vom Typ                                       │
│  ├── applies_to (contract, product, category, pricelist)                    │
│  ├── valid_from                                                             │
│  ├── valid_to (nullable)                                                    │
│  └── is_active                                                              │
│                                                                             │
│  PriceAdjustmentRule                                                        │
│  ├── id (PK)                                                                │
│  ├── tenant_id (FK)                                                         │
│  ├── contract_id (FK, nullable) -- spezifisch oder tenant-weit              │
│  ├── customer_id (FK, nullable)                                             │
│  ├── type (inflation, manual, pricelist_follow)                             │
│  ├── percentage (nullable)                                                  │
│  ├── anchor_date (z.B. 01-01 für 1. Januar)                                 │
│  ├── valid_from                                                             │
│  ├── valid_to (nullable)                                                    │
│  └── is_active                                                              │
│                                                                             │
│  ScheduledPriceChange                                                       │
│  ├── id (PK)                                                                │
│  ├── contract_id (FK)                                                       │
│  ├── contract_item_id (FK, nullable)                                        │
│  ├── new_price                                                              │
│  ├── effective_date                                                         │
│  ├── reason                                                                 │
│  └── applied_at (nullable) -- wann wurde es angewendet                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ BENACHRICHTIGUNGEN                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NotificationRule                                                           │
│  ├── id (PK)                                                                │
│  ├── tenant_id (FK)                                                         │
│  ├── event_type (contract_ending, price_change, ...)                        │
│  ├── days_before                                                            │
│  ├── channels (JSON) -- [email, slack, teams]                               │
│  └── is_active                                                              │
│                                                                             │
│  Notification                                                               │
│  ├── id (PK)                                                                │
│  ├── tenant_id (FK)                                                         │
│  ├── rule_id (FK)                                                           │
│  ├── related_object_type                                                    │
│  ├── related_object_id                                                      │
│  ├── message                                                                │
│  ├── sent_at                                                                │
│  └── channels_sent (JSON)                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Development Guidelines
- use TDD
- commit only when all tests are green
- always create unit tests for front- and backend
- Use some selected E2E Tests with Playwright to check if a complete feature works (or just login)
- make the dev environment use docker compose locally, so the developers has nothing else to install
- github workflows shall run tests on branches, build images on merge requests, pushing building final images when merged to main
- use semantic versioning (together with git tags)

## Target for Production
- k8s or swarm running linux
- 
