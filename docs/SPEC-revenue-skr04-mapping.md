# Erlöskonten-Zuordnung (SKR04) & Debitoren-Konten

## Übersicht

Einnahmen bzw. Rechnungen auf Basis von Line Items sollen den Erlöskonten des SKR04-Kontenrahmens zugeordnet werden. Zusätzlich erhalten Kunden individuelle Debitoren-Kontonummern. Damit wird eine saubere Übergabe an die Buchhaltung (DATEV-Export) ermöglicht.

### Ziel

1. **Erlöskonten-Zuordnung**: Jede Rechnungsposition (Line Item) wird einem SKR04-Erlöskonto zugeordnet
2. **Debitoren-Konten**: Jeder Kunde erhält eine eigene Debitoren-Kontonummer
3. **Buchungssätze**: Aus finalisierten Rechnungen werden doppelte Buchungssätze generiert
4. **DATEV-Export**: Buchungssätze können im DATEV-Format exportiert werden

### Kontext im bestehenden System

Das System hat bereits:
- ✅ Rechnungserstellung mit Billing Schedules (InvoiceRecord)
- ✅ USt-Klassifizierung (domestic / eu / non_eu) via `_classify_customer()`
- ✅ Line Items mit Produktzuordnung (ContractItem → Product)
- ✅ Produktkategorien (ProductCategory)
- ✅ Steuersätze (CompanyLegalData.default_tax_rate)
- ✅ Bankabgleich (InvoicePaymentMatch)

### Steuersatz-Logik: Default + Ausnahmen pro Produkt

Das System verwendet einen **Default-USt-Satz** (z.B. 19%), der für alle Produkte gilt.
Einzelne Produkte können einen **abweichenden Steuersatz** haben (z.B. 7% für bestimmte Leistungen).

```
Effektiver Steuersatz eines Line Items:
1. Hat das Produkt einen eigenen tax_rate? → verwende diesen
2. Sonst: verwende CompanyLegalData.default_tax_rate (z.B. 19%)
3. Ist der Kunde EU/Drittland? → 0% (Reverse Charge / steuerfrei)
```

Die Erlöskonto-Zuordnung ergibt sich automatisch aus der Kombination:
- **Produkt-Steuersatz** (default oder Ausnahme) → bestimmt Erlöskonto bei Inland
- **Kunden-Klassifizierung** (domestic/EU/non_EU) → bestimmt ob USt anfällt

---

## 1. Datenmodell

### 1.1 Produkt-Steuersatz (Erweiterung Product-Model)

Neues optionales Feld auf dem bestehenden Product-Model:

```python
# In apps/products/models.py - Product model erweitern:

tax_rate = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    null=True,
    blank=True,
    help_text="Abweichender USt-Satz in % (z.B. 7.00). Leer = Default-Steuersatz des Unternehmens.",
)
```

**Logik:**
- `Product.tax_rate = None` → Es gilt `CompanyLegalData.default_tax_rate` (z.B. 19%)
- `Product.tax_rate = 7.00` → Dieses Produkt wird immer mit 7% besteuert (Inland)
- `Product.tax_rate = 0.00` → Steuerfreies Produkt (z.B. Bildungsleistung §4 Nr.21 UStG)

**Effektiver Steuersatz (Methode):**

```python
def get_effective_tax_rate(self, default_tax_rate: Decimal) -> Decimal:
    """Gibt den effektiven Steuersatz zurück.

    Verwendet den produktspezifischen Satz oder den Default.
    Hinweis: Bei EU/Drittland-Kunden wird 0% angewendet,
    unabhängig von diesem Wert (wird in BookingService behandelt).
    """
    if self.tax_rate is not None:
        return self.tax_rate
    return default_tax_rate
```

### 1.2 RevenueAccount (Erlöskonto)

Stammdaten der SKR04-Erlöskonten. Pro Tenant konfigurierbar.

```
backend/apps/accounting/models.py
```

```python
class RevenueAccount(TenantModel):
    """SKR04-Erlöskonto für die Zuordnung von Einnahmen."""

    account_number = models.CharField(
        max_length=10,
        help_text="SKR04 Kontonummer (z.B. '4400')",
    )
    name = models.CharField(
        max_length=255,
        help_text="Kontobezeichnung (z.B. 'Erlöse 19% USt')",
    )
    description = models.TextField(
        blank=True,
        help_text="Erläuterung / Hinweis zur Verwendung",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Erwarteter Steuersatz (zur Validierung, z.B. 19.00)",
    )
    vat_classification = models.CharField(
        max_length=10,
        choices=[
            ("domestic", "Inland"),
            ("eu", "EU (Reverse Charge)"),
            ("non_eu", "Drittland"),
            ("any", "Alle"),
        ],
        default="any",
        help_text="USt-Klassifizierung für automatische Zuordnung",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "account_number"],
                name="unique_revenue_account_per_tenant",
            ),
        ]
```

**Standard-Erlöskonten (SKR04-Seed):**

| Konto | Bezeichnung | USt-Klasse | Steuersatz |
|-------|------------|------------|------------|
| 4400 | Erlöse aus Lieferungen und Leistungen 19% USt | domestic | 19% |
| 4300 | Erlöse 7% USt | domestic | 7% |
| 4125 | Steuerfreie innergemeinschaftliche Lieferungen §4 Nr.1b UStG | eu | 0% |
| 4336 | Erlöse aus im anderen EU-Land stpfl. sonstigen Leistungen | eu | 0% |
| 4338 | Erlöse aus im Drittland stpfl. sonstigen Leistungen | non_eu | 0% |
| 4200 | Erlösschmälerungen | any | — |

### 1.3 TaxAccount (Steuerkonto)

Für die MwSt-Buchung benötigte Gegenkonten.

```python
class TaxAccount(TenantModel):
    """Steuerkonto für USt-Buchungen (Gegenkonto)."""

    account_number = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "account_number"],
                name="unique_tax_account_per_tenant",
            ),
        ]
```

**Standard-Steuerkonten (SKR04):**

| Konto | Bezeichnung | Steuersatz |
|-------|------------|------------|
| 3806 | Umsatzsteuer 19% | 19% |
| 3801 | Umsatzsteuer 7% | 7% |

### 1.4 RevenueAccountMapping (Zuordnungsregel)

Automatische Zuordnung basierend auf Steuersatz + Kunden-Klassifizierung, mit optionaler manueller Überschreibung pro Produkt.

```python
class RevenueAccountMapping(TenantModel):
    """Zuordnungsregel: Steuersatz/Produkt → Erlöskonto.

    Zwei Mapping-Ebenen:
    A) Automatisch per Steuersatz + Kunden-Klassifizierung (Standard):
       - domestic + 19% → 4400
       - domestic + 7%  → 4300
       - eu             → 4336
       - non_eu         → 4338

    B) Manuell pro Produkt (Ausnahme, hat Vorrang):
       - Produkt X → immer auf Konto 4400, egal welcher Default

    Priorität (höchste zuerst):
    1. Produkt-spezifisch + USt-Klassifizierung
    2. Produkt-spezifisch + any
    3. Steuersatz + USt-Klassifizierung (automatisch)
    4. Steuersatz + any
    5. Globaler Fallback (kein Produkt, kein Steuersatz, any)
    """

    # Optionale Produkt-Zuordnung (für Ausnahmen)
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="revenue_account_mappings",
        help_text="Spezifisches Produkt (für Ausnahmen, hat Vorrang)",
    )

    # Steuersatz-basierte Zuordnung (Standard)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Steuersatz für automatische Zuordnung (z.B. 19.00, 7.00, 0.00)",
    )

    vat_classification = models.CharField(
        max_length=10,
        choices=[
            ("domestic", "Inland"),
            ("eu", "EU (Reverse Charge)"),
            ("non_eu", "Drittland"),
            ("any", "Alle (Fallback)"),
        ],
        default="any",
    )
    revenue_account = models.ForeignKey(
        RevenueAccount,
        on_delete=models.PROTECT,
        related_name="mappings",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product", "tax_rate", "vat_classification"],
                name="unique_revenue_mapping",
            ),
        ]
```

**Zuordnungs-Logik (Auflösung):**

```
Gegeben:
  - Line Item mit Produkt P
  - Produkt hat effektiven Steuersatz T (eigener oder Default)
  - Kunde hat USt-Klassifizierung V (domestic/eu/non_eu)

Auflösung:
1. Suche Mapping: product=P, vat_classification=V         → gefunden? → verwende Erlöskonto
2. Suche Mapping: product=P, vat_classification=any       → gefunden? → verwende Erlöskonto
3. Suche Mapping: tax_rate=T, vat_classification=V         → gefunden? → verwende Erlöskonto
4. Suche Mapping: tax_rate=T, vat_classification=any       → gefunden? → verwende Erlöskonto
5. Suche Mapping: product=null, tax_rate=null, vat=V       → Globaler Fallback per Klasse
6. Suche Mapping: product=null, tax_rate=null, vat=any     → Globaler Fallback
7. Nichts gefunden → Warnung, kein Erlöskonto zugeordnet
```

**Typisches Setup (automatisch bei SKR04-Seed):**

| Produkt | Steuersatz | USt-Klasse | Erlöskonto |
|---------|-----------|------------|------------|
| — | 19.00 | domestic | 4400 (Erlöse 19%) |
| — | 7.00 | domestic | 4300 (Erlöse 7%) |
| — | — | eu | 4336 (Erlöse EU ig. sonstige Leist.) |
| — | — | non_eu | 4338 (Erlöse Drittland) |

So reicht es, auf einem Produkt `tax_rate = 7.00` zu setzen, und die Zuordnung
auf Konto 4300 erfolgt automatisch. Für EU/Drittland-Kunden greift immer das
Klassifizierungs-Mapping, unabhängig vom Produkt-Steuersatz.

### 1.5 Debitoren-Konten (flexibles Mapping)

Die konkreten Debitoren-Kontonummern sind primär für den DATEV-Export relevant.
Im laufenden Betrieb reicht es, dass pro Kunde ein Konto geführt wird.
Das eigentliche Nummern-Mapping passiert **vor dem Export**, damit es mit
bestehenden DATEV-Bestandsdaten zusammenpasst.

**Konzept: Zweistufig — internes Konto + Export-Mapping**

```
Stufe 1 (laufend):   Customer ←→ DebitorAccount  (interne Zuordnung, ohne feste Nummer)
Stufe 2 (vor Export): DebitorAccount → Kontonummer  (DATEV-Mapping, flexibel anpassbar)
```

```python
class DebitorAccount(TenantModel):
    """Debitoren-Konto: Verbindung zwischen Kunde und Buchhaltung.

    Die Kontonummer kann leer bleiben und wird erst vor dem Export
    zugewiesen — manuell oder automatisch. So können bestehende
    DATEV-Nummern importiert und abgeglichen werden.
    """

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="debitor_account",
    )
    account_number = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="DATEV-Kontonummer (z.B. '10001'). Leer = noch nicht zugewiesen.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Hinweise (z.B. 'Altsystem: D-4711', 'Zusammenlegung mit X')",
    )

    class Meta:
        ordering = ["account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "account_number"],
                condition=models.Q(account_number__gt=""),
                name="unique_debitor_number_per_tenant",
            ),
        ]

    def __str__(self):
        num = self.account_number or "(ohne Nummer)"
        return f"Debitor {num} – {self.customer}"
```

**DebitorAccountScheme (Nummernkreis-Konfiguration):**

```python
class DebitorAccountScheme(TimestampedModel):
    """Konfiguration für die automatische Vergabe von Debitoren-Kontonummern.

    Wird beim Auto-Assign vor dem Export verwendet.
    """

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="debitor_account_scheme",
    )
    prefix = models.CharField(
        max_length=5,
        default="",
        blank=True,
        help_text="Optionales Präfix (z.B. 'D' → D10001)",
    )
    start_number = models.PositiveIntegerField(
        default=10000,
        help_text="Startnummer für Debitoren-Konten (Standard SKR04: 10000)",
    )
    next_number = models.PositiveIntegerField(
        default=10001,
        help_text="Nächste zu vergebende Nummer",
    )
    end_number = models.PositiveIntegerField(
        default=69999,
        help_text="Höchste erlaubte Nummer (Standard SKR04: 69999)",
    )
```

**Vergabe-Logik (flexibel, vor Export):**

```
Zeitpunkt der Nummernvergabe:
- NICHT bei Rechnungs-Finalisierung (zu früh)
- VOR dem DATEV-Export: Validierung zeigt Kunden ohne Nummer
- Nutzer entscheidet: manuell zuweisen ODER auto-assign

Ablauf vor Export:
1. System zeigt: "5 Kunden ohne Debitorennummer"
2. Nutzer kann:
   a) Einzeln manuell zuweisen (z.B. bestehende DATEV-Nummer übernehmen)
   b) DATEV-Bestandsdaten importieren (CSV: Kundenname → Kontonummer)
   c) "Alle fehlenden automatisch vergeben" (ab next_number)
3. Erst wenn alle Kunden im Zeitraum eine Nummer haben → Export möglich
```

**Import bestehender DATEV-Nummern:**

```
CSV-Import: Kundenname/Kunden-Nr. → Debitorennummer
┌──────────────────┬─────────────────┐
│ Kunde            │ Debitor-Konto   │
├──────────────────┼─────────────────┤
│ Muster GmbH      │ 10001           │
│ TechCorp B.V.    │ 10015           │
│ US Corp Inc.      │ 10023           │
└──────────────────┴─────────────────┘

→ Matching per Kundenname oder Kunden-Nr.
→ Konflikte werden angezeigt (z.B. Nummer bereits vergeben)
```

### 1.6 BookingEntry (Buchungssatz)

Generierte Buchungssätze aus finalisierten Rechnungen.

```python
class BookingEntry(TenantModel):
    """Ein einzelner Buchungssatz aus einer Rechnung."""

    invoice_record = models.ForeignKey(
        "invoices.InvoiceRecord",
        on_delete=models.CASCADE,
        related_name="booking_entries",
    )
    booking_date = models.DateField(
        help_text="Buchungsdatum (= Rechnungsdatum)",
    )
    debit_account = models.CharField(
        max_length=10,
        help_text="Soll-Konto (Debitor oder Erlöskonto)",
    )
    credit_account = models.CharField(
        max_length=10,
        help_text="Haben-Konto (Erlöskonto oder Steuerkonto)",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    tax_key = models.CharField(
        max_length=5,
        blank=True,
        help_text="DATEV Steuerschlüssel (z.B. '9' für 19% USt)",
    )
    description = models.CharField(
        max_length=255,
        help_text="Buchungstext (z.B. 'RE 2026-0042 / Kunde XY / Produkt Z')",
    )
    cost_center = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optionale Kostenstelle (KOST1)",
    )

    # Referenz auf Line Item (für Nachvollziehbarkeit)
    line_item_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Snapshot des Line Items zum Zeitpunkt der Buchung",
    )

    class Meta:
        ordering = ["booking_date", "invoice_record", "id"]
        indexes = [
            models.Index(fields=["tenant", "booking_date"]),
            models.Index(fields=["tenant", "debit_account"]),
            models.Index(fields=["tenant", "credit_account"]),
        ]
```

### 1.7 AccountingExport (Export-Tracking)

```python
class AccountingExport(TenantModel):
    """Protokollierung von DATEV-Exporten."""

    class ExportFormat(models.TextChoices):
        DATEV_CSV = "datev_csv", "DATEV Buchungsstapel (CSV)"
        DATEV_XML = "datev_xml", "DATEV XML"

    period_start = models.DateField()
    period_end = models.DateField()
    export_format = models.CharField(
        max_length=20,
        choices=ExportFormat.choices,
        default=ExportFormat.DATEV_CSV,
    )
    file = models.FileField(
        upload_to="uploads/%(tenant_id)s/accounting/exports/",
        blank=True,
    )
    entry_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    exported_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
```

---

## 2. Buchungs-Logik

### 2.1 Buchungssatz-Schema pro Rechnung

Für jede finalisierte Rechnung (InvoiceRecord) werden Buchungssätze generiert:

#### Fall A: Inlandsrechnung (domestic, 19% USt)

```
Rechnung RE-2026-0042 an Kunde "Muster GmbH" (Debitor 10001)
- Line Item 1: Software Maintenance, 500,00 EUR → Konto 4400
- Line Item 2: Hosting, 300,00 EUR                → Konto 4400
- MwSt 19%: 152,00 EUR

Buchungssätze:
┌────────────────────────────────────────────────────────────────┐
│ Soll        │ Haben  │ Betrag   │ Steuerschl. │ Text         │
├─────────────┼────────┼──────────┼─────────────┼──────────────┤
│ 10001       │ 4400   │ 500,00   │ 9 (19%)     │ RE-2026-0042 │
│ 10001       │ 4400   │ 300,00   │ 9 (19%)     │ RE-2026-0042 │
└────────────────────────────────────────────────────────────────┘

Hinweis: Bei DATEV-Buchungsstapel mit Steuerschlüssel rechnet
DATEV die USt automatisch (Automatikkonto). Daher nur Netto-Beträge
mit Steuerschlüssel. Alternative: Explizite Brutto-Buchung ohne
Automatik.
```

#### Fall B: EU-Rechnung (Reverse Charge)

```
Rechnung RE-2026-0043 an "TechCorp B.V." (NL, Debitor 10015)
- Line Item 1: SaaS License, 1.000,00 EUR → Konto 4336
- MwSt: 0,00 EUR (Reverse Charge)

Buchungssätze:
┌────────────────────────────────────────────────────────────────┐
│ Soll        │ Haben  │ Betrag    │ Steuerschl. │ Text         │
├─────────────┼────────┼───────────┼─────────────┼──────────────┤
│ 10015       │ 4336   │ 1.000,00  │ 0 (stfr.)   │ RE-2026-0043 │
└────────────────────────────────────────────────────────────────┘
```

#### Fall C: Drittland-Rechnung (non-EU)

```
Rechnung RE-2026-0044 an "US Corp Inc." (US, Debitor 10023)
- Line Item 1: Consulting, 2.500,00 EUR → Konto 4338

Buchungssätze:
┌────────────────────────────────────────────────────────────────┐
│ Soll        │ Haben  │ Betrag    │ Steuerschl. │ Text         │
├─────────────┼────────┼───────────┼─────────────┼──────────────┤
│ 10023       │ 4338   │ 2.500,00  │ 0 (stfr.)   │ RE-2026-0044 │
└────────────────────────────────────────────────────────────────┘
```

#### Fall D: Storno (Gutschrift)

Buchungssätze werden umgekehrt (Soll/Haben getauscht oder Negativbetrag).

### 2.2 Buchungssatz-Generierung (Service)

```python
# backend/apps/accounting/services.py

class BookingService:
    """Generiert Buchungssätze aus finalisierten Rechnungen."""

    def generate_bookings(self, invoice_record: InvoiceRecord) -> list[BookingEntry]:
        """Generiert Buchungssätze für eine einzelne Rechnung.

        Wird aufgerufen wenn:
        - Eine Rechnung finalisiert wird (Status → finalized)
        - Manuell über die UI angestoßen

        Schritte:
        1. Debitor-Konto des Kunden nachschlagen
           (Fehler wenn nicht vorhanden — muss vor Export zugewiesen sein)
        2. USt-Klassifizierung bestimmen (domestic/eu/non_eu)
        3. Für jeden Line Item:
           a. Effektiven Steuersatz bestimmen (Produkt.tax_rate oder Default)
           b. Produkt + Steuersatz → RevenueAccountMapping auflösen
           c. Bei Inland: Steuersatz anwenden, bei EU/Drittland: 0%
           d. BookingEntry erstellen (Debitor → Erlöskonto)
        4. Storno-Fall: Beträge negieren
        """

    def generate_bookings_for_period(
        self, tenant: Tenant, start: date, end: date
    ) -> list[BookingEntry]:
        """Generiert/aktualisiert Buchungssätze für alle Rechnungen
        eines Zeitraums."""

    def resolve_revenue_account(
        self,
        tenant: Tenant,
        product: Product | None,
        effective_tax_rate: Decimal,
        vat_classification: str,
    ) -> RevenueAccount | None:
        """Löst das Erlöskonto nach der Prioritätskette auf.

        Berücksichtigt:
        1. Produkt-spezifische Mappings (Ausnahmen)
        2. Steuersatz-basierte Mappings (Standard)
        3. Globalen Fallback

        effective_tax_rate: Der Steuersatz des Produkts
        (product.tax_rate oder default_tax_rate).
        Gibt None zurück wenn kein Mapping gefunden."""

    def export_datev(
        self,
        tenant: Tenant,
        start: date,
        end: date,
        format: str = "datev_csv",
    ) -> AccountingExport:
        """Exportiert Buchungssätze im DATEV-Format."""
```

### 2.3 DATEV Buchungsstapel (CSV-Format)

Der Export folgt dem DATEV-Buchungsstapel-Format (CSV mit Header):

```csv
"Umsatz (ohne Soll/Haben-Kz)";"Soll/Haben-Kennzeichen";"WKZ Umsatz";"Kurs";"Basis-Umsatz";"WKZ Basis-Umsatz";"Konto";"Gegenkonto (ohne BU-Schlüssel)";"BU-Schlüssel";"Belegdatum";"Belegfeld 1";"Belegfeld 2";"Skonto";"Buchungstext";"Postensperre";"Diverse Adressnummer";"Geschäftspartnerbank";"Sachverhalt";"Zinssperre";"Beleglink";"Beleginfo - Art 1";"Beleginfo - Inhalt 1";"Beleginfo - Art 2";"Beleginfo - Inhalt 2";"Beleginfo - Art 3";"Beleginfo - Inhalt 3";"Beleginfo - Art 4";"Beleginfo - Inhalt 4";"Beleginfo - Art 5";"Beleginfo - Inhalt 5";"Beleginfo - Art 6";"Beleginfo - Inhalt 6";"Beleginfo - Art 7";"Beleginfo - Inhalt 7";"Beleginfo - Art 8";"Beleginfo - Inhalt 8";"KOST1 - Kostenstelle";"KOST2 - Kostenstelle";"Kost-Menge";"EU-Land u. UStID";"EU-Steuersatz";"Abw. Versteuerungsart";"Sachverhalt L+L";"Funktionsergänzung L+L";"BU 49 Hauptfunktionstyp";"BU 49 Hauptfunktionsnummer";"BU 49 Funktionsergänzung";"Zusatzinformation - Art 1";"Zusatzinformation - Inhalt 1";"Zusatzinformation - Art 2";"Zusatzinformation - Inhalt 2";"Zusatzinformation - Art 3";"Zusatzinformation - Inhalt 3";"Zusatzinformation - Art 4";"Zusatzinformation - Inhalt 4";"Zusatzinformation - Art 5";"Zusatzinformation - Inhalt 5";"Zusatzinformation - Art 6";"Zusatzinformation - Inhalt 6";"Zusatzinformation - Art 7";"Zusatzinformation - Inhalt 7";"Zusatzinformation - Art 8";"Zusatzinformation - Inhalt 8";"Zusatzinformation - Art 9";"Zusatzinformation - Inhalt 9";"Zusatzinformation - Art 10";"Zusatzinformation - Inhalt 10";"Zusatzinformation - Art 11";"Zusatzinformation - Inhalt 11";"Zusatzinformation - Art 12";"Zusatzinformation - Inhalt 12";"Zusatzinformation - Art 13";"Zusatzinformation - Inhalt 13";"Zusatzinformation - Art 14";"Zusatzinformation - Inhalt 14";"Zusatzinformation - Art 15";"Zusatzinformation - Inhalt 15";"Zusatzinformation - Art 16";"Zusatzinformation - Inhalt 16";"Zusatzinformation - Art 17";"Zusatzinformation - Inhalt 17";"Zusatzinformation - Art 18";"Zusatzinformation - Inhalt 18";"Zusatzinformation - Art 19";"Zusatzinformation - Inhalt 19";"Zusatzinformation - Art 20";"Zusatzinformation - Inhalt 20";"Stück";"Gewicht";"Zahlweise";"Forderungsart";"Veranlagungsjahr";"Zugeordnete Fälligkeit";"Skontotyp";"Auftragsnummer";"Buchungstyp";"Ust-Schlüssel (Anzahlungen)";"EU-Land (Anzahlungen)";"Sachverhalt L+L (Anzahlungen)";"EU-Steuersatz (Anzahlungen)";"Erlöskonto (Anzahlungen)";"Herkunft-Kz";"Buchungs GUID";"KOST-Datum";"SEPA-Mandatsreferenz";"Skontosperre";"Gesellschaftername";"Beteiligtennummer";"Identifikationsnummer";"Zeichnernummer";"Postensperre bis";"Bezeichnung SoBil-Sachverhalt";"Kennzeichen SoBil-Buchung";"Festschreibung";"Leistungsdatum";"Datum Zuord. Steuerperiode"
500,00;"S";"EUR";;;;"10001";"4400";"9";"2602";"RE-2026-0042";;;"Software Maintenance";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"";"2602"
```

**Vereinfachte relevante Felder:**

| Feld | Beschreibung | Beispiel |
|------|-------------|----------|
| Umsatz | Netto-Betrag | 500,00 |
| S/H-Kz | S=Soll, H=Haben | S |
| Konto | Debitor-Konto | 10001 |
| Gegenkonto | Erlöskonto | 4400 |
| BU-Schlüssel | Steuerschlüssel | 9 (=19%) |
| Belegdatum | Rechnungsdatum | TTMM (2602) |
| Belegfeld 1 | Rechnungsnummer | RE-2026-0042 |
| Buchungstext | Beschreibung | Software Maintenance |
| EU-Land u. UStID | Bei EU-Kunden | NL NL123456789 |
| Leistungsdatum | Leistungszeitraum | TTMM |

**DATEV Steuerschlüssel (BU-Schlüssel):**

| Schlüssel | Bedeutung |
|-----------|-----------|
| 9 | USt 19% (Automatikkonto) |
| 8 | USt 7% (Automatikkonto) |
| 0 | Keine Steuer / steuerfrei |
| 10 | Innergemeinschaftliche Lieferung §4 Nr.1b |
| 11 | Steuerpflichtige ig. sonstige Leistung |
| 19 | §13b UStG (Reverse Charge) |

---

## 3. GraphQL API

### 3.1 Queries

```graphql
# Erlöskonten
type RevenueAccountType {
  id: ID!
  accountNumber: String!
  name: String!
  description: String!
  taxRate: Decimal
  vatClassification: String!
  isActive: Boolean!
  sortOrder: Int!
  # Computed
  mappingCount: Int!          # Anzahl Zuordnungen zu diesem Konto
}

type TaxAccountType {
  id: ID!
  accountNumber: String!
  name: String!
  taxRate: Decimal!
  isActive: Boolean!
}

# Zuordnungsregeln
type RevenueAccountMappingType {
  id: ID!
  product: ProductType
  productCategory: ProductCategoryType
  vatClassification: String!
  revenueAccount: RevenueAccountType!
}

# Debitoren
type DebitorAccountSchemeType {
  prefix: String!
  startNumber: Int!
  nextNumber: Int!
  endNumber: Int!
}

type DebitorAccountType {
  id: ID!
  customer: CustomerType!
  accountNumber: String!
  notes: String!
  createdAt: DateTime!
}

type Query {
  # ...bestehende Queries...

  # Debitoren (für Export-Vorbereitung)
  debitorAccounts(
    hasNumber: Boolean          # true=nur mit Nummer, false=nur ohne
  ): [DebitorAccountType!]!
  debitorAccountScheme: DebitorAccountSchemeType
  customersWithoutDebitor: [CustomerType!]!
}

# Buchungssätze
type BookingEntryType {
  id: ID!
  invoiceRecord: InvoiceRecordType!
  bookingDate: Date!
  debitAccount: String!
  creditAccount: String!
  amount: Decimal!
  taxRate: Decimal!
  taxKey: String!
  description: String!
  costCenter: String!
  lineItemSnapshot: JSON
}

# Accounting Export
type AccountingExportType {
  id: ID!
  periodStart: Date!
  periodEnd: Date!
  exportFormat: String!
  entryCount: Int!
  totalAmount: Decimal!
  exportedBy: UserType
  createdAt: DateTime!
  downloadUrl: String
}

# Queries
type Query {
  # Erlöskonten verwalten
  revenueAccounts(isActive: Boolean): [RevenueAccountType!]!
  revenueAccount(id: ID!): RevenueAccountType

  # Steuerkonten
  taxAccounts(isActive: Boolean): [TaxAccountType!]!

  # Zuordnungen
  revenueAccountMappings: [RevenueAccountMappingType!]!
  resolveRevenueAccount(
    productId: ID
    vatClassification: String!
  ): RevenueAccountType

  # Debitoren-Schema
  debitorAccountScheme: DebitorAccountSchemeType

  # Buchungssätze
  bookingEntries(
    periodStart: Date!
    periodEnd: Date!
    accountNumber: String
  ): [BookingEntryType!]!

  bookingEntriesForInvoice(invoiceRecordId: ID!): [BookingEntryType!]!

  # Exporte
  accountingExports: [AccountingExportType!]!

  # Dashboard / Validierung
  accountingValidation(
    periodStart: Date!
    periodEnd: Date!
  ): AccountingValidationType!
}

type AccountingValidationType {
  """Validierungsergebnis für einen Zeitraum."""
  totalInvoices: Int!
  invoicesWithBookings: Int!
  invoicesWithoutBookings: Int!
  unmappedLineItems: [UnmappedLineItemType!]!
  customersWithoutDebitor: [CustomerType!]!
}

type UnmappedLineItemType {
  invoiceRecord: InvoiceRecordType!
  productName: String!
  amount: Decimal!
  reason: String!
}
```

### 3.2 Mutations

```graphql
type Mutation {
  # Erlöskonten CRUD
  createRevenueAccount(input: RevenueAccountInput!): RevenueAccountType!
  updateRevenueAccount(id: ID!, input: RevenueAccountInput!): RevenueAccountType!
  deleteRevenueAccount(id: ID!): Boolean!
  seedDefaultRevenueAccounts: [RevenueAccountType!]!   # SKR04-Standard anlegen

  # Steuerkonten CRUD
  createTaxAccount(input: TaxAccountInput!): TaxAccountType!
  updateTaxAccount(id: ID!, input: TaxAccountInput!): TaxAccountType!
  deleteTaxAccount(id: ID!): Boolean!

  # Zuordnungsregeln CRUD
  createRevenueAccountMapping(input: RevenueAccountMappingInput!): RevenueAccountMappingType!
  updateRevenueAccountMapping(id: ID!, input: RevenueAccountMappingInput!): RevenueAccountMappingType!
  deleteRevenueAccountMapping(id: ID!): Boolean!

  # Debitoren (flexibles Mapping — vor Export)
  updateDebitorAccountScheme(input: DebitorAccountSchemeInput!): DebitorAccountSchemeType!
  assignDebitorAccount(
    customerId: ID!
    accountNumber: String     # null = auto-assign nächste freie Nummer
  ): DebitorAccountType!
  bulkAssignDebitorAccounts(
    customerIds: [ID!]        # null = alle ohne Nummer, sonst nur diese
  ): BulkAssignResult!
  importDebitorAccounts(
    mappings: [DebitorImportInput!]!  # CSV-Import: Kunde → Nummer
  ): DebitorImportResult!

  # Buchungssätze generieren
  generateBookings(invoiceRecordId: ID!): [BookingEntryType!]!
  generateBookingsForPeriod(
    periodStart: Date!
    periodEnd: Date!
    regenerate: Boolean = false   # Bestehende überschreiben?
  ): GenerateBookingsResult!

  # DATEV-Export
  exportDatev(
    periodStart: Date!
    periodEnd: Date!
    format: String = "datev_csv"
  ): AccountingExportType!
}

type GenerateBookingsResult {
  created: Int!
  skipped: Int!
  errors: [String!]!
}

input RevenueAccountInput {
  accountNumber: String!
  name: String!
  description: String
  taxRate: Decimal
  vatClassification: String
  isActive: Boolean
  sortOrder: Int
}

input RevenueAccountMappingInput {
  productId: ID
  productCategoryId: ID
  vatClassification: String!
  revenueAccountId: ID!
}

input DebitorAccountSchemeInput {
  prefix: String
  startNumber: Int
  nextNumber: Int
  endNumber: Int
}

input DebitorImportInput {
  customerNumber: String      # Matching per Kunden-Nr. (CUS174)
  customerName: String        # Fallback-Matching per Name
  accountNumber: String!      # Debitorennummer aus DATEV
}

type DebitorAccountType {
  id: ID!
  customer: CustomerType!
  accountNumber: String!
  notes: String!
  createdAt: DateTime!
}

type BulkAssignResult {
  assigned: Int!
  skipped: Int!
  errors: [String!]!
}

type DebitorImportResult {
  matched: Int!
  created: Int!
  conflicts: [DebitorImportConflict!]!
}

type DebitorImportConflict {
  customerName: String!
  importedNumber: String!
  existingNumber: String!
  reason: String!
}
```

---

## 4. UI Design

### 4.1 Settings-Seite: Neuer Tab "Buchhaltung"

Route: `/settings` → Tab "Buchhaltung" / "Accounting"

```
┌─────────────────────────────────────────────────────────────────┐
│ Einstellungen                                                   │
├──────────┬──────────┬────────────┬──────────────────────────────┤
│ Allgemein│ Rechnung │ HubSpot    │ ★ Buchhaltung                │
└──────────┴──────────┴────────────┴──────────────────────────────┘

┌─ Erlöskonten (SKR04) ──────────────────────────────────────────┐
│                                                                 │
│  [SKR04-Standard laden]              [+ Erlöskonto hinzufügen]  │
│                                                                 │
│  ┌─────────┬──────────────────────────────────┬─────────┬─────┐│
│  │ Konto   │ Bezeichnung                      │ USt     │     ││
│  ├─────────┼──────────────────────────────────┼─────────┼─────┤│
│  │ 4400    │ Erlöse 19% USt                   │ 19%     │ ✏️ 🗑││
│  │ 4300    │ Erlöse 7% USt                    │ 7%      │ ✏️ 🗑││
│  │ 4336    │ Erlöse EU ig. sonstige Leist.    │ 0%      │ ✏️ 🗑││
│  │ 4338    │ Erlöse Drittland                 │ 0%      │ ✏️ 🗑││
│  │ 4125    │ Steuerfreie ig. Lieferungen      │ 0%      │ ✏️ 🗑││
│  └─────────┴──────────────────────────────────┴─────────┴─────┘│
│                                                                 │
├─ Steuerkonten ──────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┬──────────────────────────────────┬─────────┬─────┐│
│  │ 3806    │ Umsatzsteuer 19%                 │ 19%     │ ✏️ 🗑││
│  │ 3801    │ Umsatzsteuer 7%                  │ 7%      │ ✏️ 🗑││
│  └─────────┴──────────────────────────────────┴─────────┴─────┘│
│                                                                 │
├─ Debitoren-Nummernkreis ────────────────────────────────────────┤
│                                                                 │
│  Präfix:      [     ]     (optional, z.B. "D")                  │
│  Start:       [ 10000 ]                                         │
│  Nächste Nr.: [ 10001 ]                                         │
│  Ende:        [ 69999 ]                                         │
│                                                                 │
│  [Speichern]                                                    │
│                                                                 │
├─ Erlöskonto-Zuordnungen ───────────────────────────────────────┤
│                                                                 │
│  [+ Zuordnung hinzufügen]                                       │
│                                                                 │
│  ┌───────────────────┬────────────┬──────────────────────┬─────┐│
│  │ Produkt/Kategorie │ USt-Klasse │ Erlöskonto           │     ││
│  ├───────────────────┼────────────┼──────────────────────┼─────┤│
│  │ — (Fallback)      │ Inland     │ 4400 Erlöse 19%      │ ✏️ 🗑││
│  │ — (Fallback)      │ EU         │ 4336 Erlöse EU       │ ✏️ 🗑││
│  │ — (Fallback)      │ Drittland  │ 4338 Erlöse Drittl.  │ ✏️ 🗑││
│  │ Kat: Hosting      │ Inland     │ 4400 Erlöse 19%      │ ✏️ 🗑││
│  │ Prod: Consulting  │ Alle       │ 4400 Erlöse 19%      │ ✏️ 🗑││
│  └───────────────────┴────────────┴──────────────────────┴─────┘│
│                                                                 │
│  ℹ️  Priorität: Produkt > Steuersatz > Fallback                  │
│     Bei gleicher Ebene: spezifische USt-Klasse > "Alle"         │
│                                                                 │
├─ USt-Satz pro Produkt (Ausnahmen) ──────────────────────────────┤
│                                                                 │
│  Default-USt-Satz: 19,00% (aus Unternehmensdaten)               │
│                                                                 │
│  Produkte mit abweichendem Steuersatz:                          │
│  ┌──────────────────────────────┬──────────────┬───────────────┐│
│  │ Produkt                      │ USt-Satz     │ Erlöskonto    ││
│  ├──────────────────────────────┼──────────────┼───────────────┤│
│  │ Schulung / Training          │ 7,00%        │ → 4300        ││
│  │ E-Book Download              │ 7,00%        │ → 4300        ││
│  │ Bildungsleistung §4 Nr.21    │ 0,00%        │ → (manuell)   ││
│  └──────────────────────────────┴──────────────┴───────────────┘│
│                                                                 │
│  ℹ️  Produkte ohne eigenen Steuersatz verwenden den Default      │
│     (19%). Der Steuersatz bestimmt automatisch das Erlöskonto.  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Kunden-Detail: Debitoren-Konto (optional sichtbar)

Im Customer-Detail wird das Debitorenkonto angezeigt, wenn vorhanden.
Kein Pflichtfeld — die Nummer wird vor dem Export zugewiesen.

```
┌─ Kundendaten ───────────────────────────────────────────────────┐
│                                                                  │
│  Name:              Muster GmbH                                  │
│  Kunden-Nr.:        CUS174                                       │
│  Debitor-Konto:     10001        (oder "—" wenn noch nicht)     │
│  USt-IdNr.:         DE123456789                                  │
│  ...                                                             │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Rechnungsübersicht: Buchungssätze

Im bestehenden Rechnungs-Detail oder als Expand-Row:

```
┌─ Rechnung RE-2026-0042 ────────────────────────────────────────┐
│                                                                  │
│  Kunde:    Muster GmbH (Debitor 10001)                          │
│  Datum:    26.02.2026                                           │
│  Netto:    800,00 EUR                                           │
│  MwSt:     152,00 EUR (19%)                                    │
│  Brutto:   952,00 EUR                                           │
│                                                                  │
│  ┌─ Buchungssätze ─────────────────────────────────────────────┐│
│  │ Soll   │ Haben  │ Betrag   │ BU │ Text                     ││
│  ├────────┼────────┼──────────┼────┼──────────────────────────┤│
│  │ 10001  │ 4400   │ 500,00   │ 9  │ Software Maintenance     ││
│  │ 10001  │ 4400   │ 300,00   │ 9  │ Hosting                  ││
│  └────────┴────────┴──────────┴────┴──────────────────────────┘│
│                                                                  │
│  [Buchungen generieren]  [DATEV exportieren]                    │
└──────────────────────────────────────────────────────────────────┘
```

### 4.4 Neue Seite: Buchhaltungs-Export

Route: `/accounting` oder `/settings/accounting/export`

Der Export-Flow enthält den zentralen Schritt **Debitoren-Mapping** — hier
werden Kontonummern zugewiesen, bevor der Export generiert wird.

```
┌─ DATEV-Export ──────────────────────────────────────────────────┐
│                                                                  │
│  Zeitraum:  [02/2026 ▼]  bis  [02/2026 ▼]                      │
│  Format:    [DATEV Buchungsstapel (CSV) ▼]                      │
│                                                                  │
│  ┌─ Schritt 1: Validierung ───────────────────────────────────┐│
│  │                                                              ││
│  │  ✅ 42 Rechnungen mit Erlöskonto-Zuordnung                   ││
│  │  ❌ 1 Line Item ohne Erlöskonto-Zuordnung                    ││
│  │                                                              ││
│  │  [Details anzeigen]                                          ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─ Schritt 2: Debitoren-Mapping ─────────────────────────────┐│
│  │                                                              ││
│  │  ✅ 28 Kunden mit Debitorennummer                             ││
│  │  ⚠️  5 Kunden ohne Debitorennummer:                           ││
│  │                                                              ││
│  │  ┌──────────────────┬────────────┬──────────────┬──────────┐││
│  │  │ Kunde            │ Kunden-Nr. │ Debitor-Kto. │          │││
│  │  ├──────────────────┼────────────┼──────────────┼──────────┤││
│  │  │ NewCo GmbH        │ CUS412     │ [        ]   │ [Auto]   │││
│  │  │ StartupX UG       │ CUS418     │ [        ]   │ [Auto]   │││
│  │  │ Alpha Ltd.         │ CUS423     │ [        ]   │ [Auto]   │││
│  │  │ Beta Corp          │ CUS425     │ [        ]   │ [Auto]   │││
│  │  │ Gamma S.A.         │ CUS431     │ [        ]   │ [Auto]   │││
│  │  └──────────────────┴────────────┴──────────────┴──────────┘││
│  │                                                              ││
│  │  [DATEV-Nummern importieren (CSV)]                           ││
│  │  [Alle fehlenden automatisch vergeben]                       ││
│  │                                                              ││
│  │  Nächste freie Nummer: 10029  (Bereich: 10000–69999)         ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  [Exportieren]  (erst aktiv wenn alle Kunden eine Nummer haben)  │
│                                                                  │
│  ┌─ Bisherige Exporte ─────────────────────────────────────────┐│
│  │ Datum       │ Zeitraum     │ Einträge │ Betrag    │         ││
│  │ 26.02.2026  │ 01-02/2026   │ 156      │ 45.200€   │ ⬇️      ││
│  │ 01.02.2026  │ 01/2026      │ 89       │ 28.100€   │ ⬇️      ││
│  └─────────────┴──────────────┴──────────┴───────────┴─────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Implementierungsplan

### Phase 1: Backend Models & Seed (Basis)

1. Product-Model erweitern: `tax_rate` (optionaler abweichender Steuersatz)
2. Neue Django App `backend/apps/accounting/` erstellen
3. Models: `RevenueAccount`, `TaxAccount`, `RevenueAccountMapping`, `DebitorAccount`, `DebitorAccountScheme`, `BookingEntry`, `AccountingExport`
4. Migrations erstellen (products + accounting)
6. Management-Command: `seed_skr04_accounts` (Standard-Konten + Default-Mappings anlegen)
7. Tests für Models

### Phase 2: Buchungs-Service

1. `BookingService.resolve_revenue_account()` – Mapping-Auflösung
2. `BookingService.generate_bookings()` – Buchungssätze pro Rechnung
3. `BookingService.generate_bookings_for_period()` – Batch
4. Debitor-Nummern-Vergabe: manuell, CSV-Import, Auto-Assign (vor Export)
5. Tests für Service-Logik

### Phase 3: DATEV-Export

1. DATEV CSV Header generieren (Buchungsstapel-Format)
2. Booking Entries → DATEV Zeilen
3. EU-Land + USt-ID Handling
4. Download als ZIP (CSV + optional Stammdaten)
5. Export-Tracking (AccountingExport)
6. Tests für Export-Format

### Phase 4: GraphQL API

1. Types: `RevenueAccountType`, `TaxAccountType`, `RevenueAccountMappingType`, etc.
2. Queries: Konten auflisten, Buchungssätze abfragen, Validierung
3. Mutations: CRUD, Seed, Generate, Export
4. Tests für Schema

### Phase 5: Frontend – Settings

1. Neuer Tab "Buchhaltung" in Settings
2. Erlöskonten-Tabelle (CRUD)
3. Steuerkonten-Tabelle
4. Zuordnungsregeln-Tabelle (Steuersatz-basiert + Produkt-Ausnahmen)
5. USt-Ausnahmen pro Produkt (Übersichtstabelle)
6. Debitoren-Nummernkreis-Form
7. "SKR04-Standard laden" Button
8. i18n (de/en)

### Phase 6: Frontend – Integration

1. Product-Detail/Liste: Steuersatz-Feld (Ausnahme-Konfiguration)
2. Customer-Detail: Debitor-Konto anzeigen (read-only, informativ)
3. Rechnungs-Detail: Buchungssätze anzeigen
4. Export-Seite: Validierung → Debitoren-Mapping → DATEV-Download
5. Export-Seite: DATEV-Import für bestehende Debitorennummern
6. i18n (de/en)

---

## 6. Offene Punkte / Entscheidungen

| # | Frage | Optionen | Empfehlung | Status |
|---|-------|----------|------------|--------|
| 1 | Steuersatz-Konfiguration | a) Pro Produkt konfigurieren b) Pro Mapping-Regel | a) Default + Ausnahmen pro Produkt | ✅ Entschieden |
| 2 | Buchungssätze automatisch bei Finalisierung generieren? | a) Automatisch b) Manuell | a) Automatisch | Offen |
| 3 | DATEV-Export: Brutto mit Automatikkonto oder Netto+USt getrennt? | a) Automatikkonto (Netto + BU-Schlüssel) b) Getrennte Buchungen | a) Automatikkonto (DATEV-Standard) | Offen |
| 4 | Storno: Negativbuchung oder Soll/Haben tauschen? | a) Negativbetrag b) Umkehrbuchung | a) Negativbetrag (DATEV-konform) | Offen |
| 5 | Kostenstellen (KOST1/KOST2)? | a) Jetzt b) Später | b) Später (optionales Feld vorbereiten) | Offen |
| 6 | Debitoren-Stammdaten DATEV-Export? | a) Nur Buchungsstapel b) + Debitoren-Stammdaten | b) Beides (als ZIP) | Offen |
| 7 | Mehrere Steuersätze pro Rechnung (gemischte Items)? | Muss unterstützt werden | Ja, pro Line Item | ✅ Entschieden |

---

## 7. Datenfluss (End-to-End)

```
                    ┌─────────────┐
                    │   Produkt   │──── tax_rate (z.B. 7%) oder NULL (→ Default 19%)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ ContractItem│──── Preis, Menge
                    └──────┬──────┘
                           │
               ┌───────────▼───────────┐
               │  InvoiceRecord        │
               │  (finalisiert)        │
               │  + line_items_snapshot │
               └───────────┬───────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │         BookingService              │
        │                                      │
        │  1. Customer → DebitorAccount          │
        │     (Nummer muss vor Export vergeben   │
        │      sein, sonst Validierungsfehler)   │
        │  2. classify_customer → domestic/eu   │
        │  3. Pro Line Item:                    │
        │     a. Effektiver USt-Satz bestimmen  │
        │        (Produkt.tax_rate || Default)  │
        │     b. Steuersatz + Klassifizierung   │
        │        → RevenueAccountMapping        │
        │        → Erlöskonto (z.B. 4400/4300)  │
        │     c. Inland: USt anwenden           │
        │        EU/Drittland: 0%               │
        │  4. BookingEntry erstellen            │
        └──────────────────┬──────────────────┘
                           │
                    ┌──────▼──────┐
                    │BookingEntry │
                    │ Soll: 10001 │
                    │ Haben: 4400 │
                    │ 500,00 EUR  │
                    │ BU: 9       │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ DATEV CSV   │
                    │ Export      │
                    └─────────────┘
```

---

## 8. i18n Schlüssel

```json
{
  "de": {
    "accounting": {
      "title": "Buchhaltung",
      "revenueAccounts": "Erlöskonten",
      "taxAccounts": "Steuerkonten",
      "mappings": "Erlöskonto-Zuordnungen",
      "debitorScheme": "Debitoren-Nummernkreis",
      "seedSkr04": "SKR04-Standard laden",
      "addAccount": "Erlöskonto hinzufügen",
      "addMapping": "Zuordnung hinzufügen",
      "accountNumber": "Kontonummer",
      "accountName": "Bezeichnung",
      "taxRate": "Steuersatz",
      "vatClassification": "USt-Klassifizierung",
      "domestic": "Inland",
      "eu": "EU (Reverse Charge)",
      "nonEu": "Drittland",
      "any": "Alle",
      "fallback": "Fallback",
      "debitorAccount": "Debitor-Konto",
      "autoAssign": "Auto-Vergabe",
      "assignAll": "Alle zuweisen",
      "bookingEntries": "Buchungssätze",
      "debitAccount": "Soll",
      "creditAccount": "Haben",
      "taxKey": "BU-Schlüssel",
      "generateBookings": "Buchungen generieren",
      "exportDatev": "DATEV exportieren",
      "export": {
        "title": "DATEV-Export",
        "period": "Zeitraum",
        "format": "Format",
        "preview": "Vorschau",
        "validation": "Validierung",
        "invoicesWithBookings": "Rechnungen mit Buchungssätzen",
        "invoicesWithout": "Rechnungen ohne Buchungssätze",
        "customersWithoutDebitor": "Kunden ohne Debitorennummer",
        "unmappedItems": "Line Items ohne Erlöskonto",
        "export": "Exportieren",
        "previousExports": "Bisherige Exporte",
        "download": "Herunterladen"
      },
      "prefix": "Präfix",
      "startNumber": "Startnummer",
      "nextNumber": "Nächste Nummer",
      "endNumber": "Endnummer",
      "priority": "Priorität: Produkt > Kategorie > Fallback"
    }
  },
  "en": {
    "accounting": {
      "title": "Accounting",
      "revenueAccounts": "Revenue Accounts",
      "taxAccounts": "Tax Accounts",
      "mappings": "Revenue Account Mappings",
      "debitorScheme": "Debtor Account Number Range",
      "seedSkr04": "Load SKR04 Defaults",
      "addAccount": "Add Revenue Account",
      "addMapping": "Add Mapping",
      "accountNumber": "Account Number",
      "accountName": "Account Name",
      "taxRate": "Tax Rate",
      "vatClassification": "VAT Classification",
      "domestic": "Domestic",
      "eu": "EU (Reverse Charge)",
      "nonEu": "Non-EU",
      "any": "All",
      "fallback": "Fallback",
      "debitorAccount": "Debtor Account",
      "autoAssign": "Auto-Assign",
      "assignAll": "Assign All",
      "bookingEntries": "Booking Entries",
      "debitAccount": "Debit",
      "creditAccount": "Credit",
      "taxKey": "Tax Key",
      "generateBookings": "Generate Bookings",
      "exportDatev": "Export DATEV",
      "export": {
        "title": "DATEV Export",
        "period": "Period",
        "format": "Format",
        "preview": "Preview",
        "validation": "Validation",
        "invoicesWithBookings": "Invoices with bookings",
        "invoicesWithout": "Invoices without bookings",
        "customersWithoutDebitor": "Customers without debtor account",
        "unmappedItems": "Line items without revenue account",
        "export": "Export",
        "previousExports": "Previous Exports",
        "download": "Download"
      },
      "prefix": "Prefix",
      "startNumber": "Start Number",
      "nextNumber": "Next Number",
      "endNumber": "End Number",
      "priority": "Priority: Product > Category > Fallback"
    }
  }
}
```

---

## 9. Testplan

### Backend Unit Tests

| Test | Beschreibung |
|------|-------------|
| `test_revenue_account_crud` | Erstellen, Lesen, Aktualisieren, Löschen von Erlöskonten |
| `test_unique_account_per_tenant` | Keine doppelten Kontonummern pro Tenant |
| `test_mapping_resolution_product_specific` | Produkt-spezifische Zuordnung hat Vorrang |
| `test_mapping_resolution_category_fallback` | Kategorie als Fallback wenn kein Produkt-Mapping |
| `test_mapping_resolution_global_fallback` | Globaler Fallback ohne Produkt/Kategorie |
| `test_mapping_resolution_vat_specific` | USt-spezifisches Mapping vor "any" |
| `test_mapping_resolution_no_match` | None wenn kein Mapping gefunden |
| `test_generate_bookings_domestic` | Buchungssätze für Inlandsrechnung (19% USt) |
| `test_generate_bookings_eu` | Buchungssätze für EU-Rechnung (Reverse Charge) |
| `test_generate_bookings_non_eu` | Buchungssätze für Drittland-Rechnung |
| `test_generate_bookings_storno` | Storno erzeugt Negativbuchungen |
| `test_generate_bookings_mixed_items` | Rechnung mit Items verschiedener Erlöskonten |
| `test_debitor_manual_assign` | Manuelle Debitor-Vergabe vor Export |
| `test_debitor_auto_assign_bulk` | Auto-Assign für alle fehlenden Nummern |
| `test_debitor_no_duplicate` | Keine doppelte Vergabe |
| `test_debitor_csv_import` | DATEV-Bestandsdaten importieren (CSV → Kontonummer) |
| `test_debitor_import_conflict` | Konflikterkennung bei Import (Nummer bereits vergeben) |
| `test_export_blocked_without_debitor` | Export nicht möglich ohne Debitorennummer |
| `test_datev_export_header` | DATEV CSV Header korrekt |
| `test_datev_export_domestic_row` | Inlandsbuchung korrekt formatiert |
| `test_datev_export_eu_row` | EU-Buchung mit USt-ID korrekt |
| `test_datev_export_period` | Export für Zeitraum enthält alle Buchungen |
| `test_seed_skr04` | Standard-Konten werden korrekt angelegt |
| `test_validation_unmapped_items` | Erkennung fehlender Zuordnungen |
| `test_validation_missing_debitor` | Erkennung fehlender Debitorennummern |

### Frontend E2E Tests

| Test | Beschreibung |
|------|-------------|
| `test_settings_accounting_tab` | Tab wird angezeigt |
| `test_revenue_accounts_crud` | Erlöskonten anlegen/bearbeiten/löschen |
| `test_seed_skr04_defaults` | Standard-Konten laden |
| `test_mapping_crud` | Zuordnungen anlegen/bearbeiten/löschen |
| `test_datev_export_debitor_mapping` | Export-Seite: Debitoren zuweisen vor Export |
| `test_datev_export_import_csv` | DATEV-Nummern per CSV importieren |
| `test_datev_export_flow` | Export-Seite: Validierung → Mapping → Download |
