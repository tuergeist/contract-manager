"""Tests for ZUGFeRD invoice generation."""
import pytest
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree as ET

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.invoices.models import CompanyLegalData, InvoiceRecord
from apps.invoices.services import InvoiceService
from apps.invoices.zugferd import ZugferdService, _resolve_country_code
from apps.products.models import Product


# Namespaces used in ZUGFeRD / CII XML
NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}


@pytest.fixture
def legal_data(db, tenant):
    return CompanyLegalData.objects.create(
        tenant=tenant,
        company_name="Test GmbH",
        street="Teststraße 1",
        zip_code="80331",
        city="München",
        country="Deutschland",
        tax_number="123/456/78901",
        vat_id="DE123456789",
        commercial_register_court="Amtsgericht München",
        commercial_register_number="HRB 12345",
        managing_directors=["Max Mustermann"],
        bank_name="Deutsche Bank",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        default_tax_rate=Decimal("19.00"),
    )


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant,
        name="Acme Corp",
        address={
            "street": "Hauptstraße 1",
            "city": "Berlin",
            "zip": "10115",
            "country": "Deutschland",
        },
        is_active=True,
    )


@pytest.fixture
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="SaaS License",
        sku="SAAS-001",
    )


@pytest.fixture
def active_contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="SaaS Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_item(db, active_contract, product):
    return ContractItem.objects.create(
        contract=active_contract,
        product=product,
        tenant=active_contract.tenant,
        quantity=1,
        unit_price=Decimal("1000.00"),
        billing_start_date=date(2026, 1, 1),
    )


@pytest.fixture
def invoice_record(db, tenant, customer, active_contract, legal_data):
    """Create a finalized InvoiceRecord for testing."""
    return InvoiceRecord.objects.create(
        tenant=tenant,
        contract=active_contract,
        customer=customer,
        invoice_number="2026-0001",
        billing_date=date(2026, 1, 1),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        total_net=Decimal("1000.00"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("190.00"),
        total_gross=Decimal("1190.00"),
        line_items_snapshot=[
            {
                "item_id": 1,
                "product_name": "SaaS License",
                "description": "Monthly license fee",
                "quantity": 1,
                "unit_price": "1000.00",
                "amount": "1000.00",
                "is_prorated": False,
                "prorate_factor": None,
                "is_one_off": False,
            }
        ],
        company_data_snapshot=legal_data.to_snapshot(),
        status=InvoiceRecord.Status.FINALIZED,
        customer_name="Acme Corp",
        contract_name="SaaS Contract",
        invoice_text="Zahlungsziel: 30 Tage netto",
    )


class TestCountryCodeResolution:
    """Test country name to ISO code resolution."""

    def test_two_letter_code_passthrough(self):
        assert _resolve_country_code("DE") == "DE"
        assert _resolve_country_code("AT") == "AT"

    def test_german_country_names(self):
        assert _resolve_country_code("Deutschland") == "DE"
        assert _resolve_country_code("Österreich") == "AT"
        assert _resolve_country_code("Schweiz") == "CH"

    def test_english_country_names(self):
        assert _resolve_country_code("Germany") == "DE"
        assert _resolve_country_code("Austria") == "AT"
        assert _resolve_country_code("Switzerland") == "CH"

    def test_case_insensitive(self):
        assert _resolve_country_code("deutschland") == "DE"
        assert _resolve_country_code("GERMANY") == "DE"

    def test_default_to_de(self):
        assert _resolve_country_code("") == "DE"
        assert _resolve_country_code("Unknown Country") == "DE"

    def test_lowercase_two_letter(self):
        assert _resolve_country_code("de") == "DE"
        assert _resolve_country_code("fr") == "FR"


class TestZugferdXmlGeneration:
    """Test ZUGFeRD XML generation from InvoiceRecord."""

    def test_generates_valid_xml(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)

        assert xml_bytes is not None
        assert len(xml_bytes) > 0

        # Should be parseable XML
        root = ET.fromstring(xml_bytes)
        assert root.tag.endswith("CrossIndustryInvoice")

    def test_xml_contains_invoice_number(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        # Find invoice number in header
        header_id = root.find(
            ".//rsm:ExchangedDocument/ram:ID", NS
        )
        assert header_id is not None
        assert header_id.text == "2026-0001"

    def test_xml_contains_type_code_380(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        type_code = root.find(
            ".//rsm:ExchangedDocument/ram:TypeCode", NS
        )
        assert type_code is not None
        assert type_code.text == "380"

    def test_xml_contains_seller_info(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        seller_name = root.find(
            ".//ram:ApplicableHeaderTradeAgreement/ram:SellerTradeParty/ram:Name", NS
        )
        assert seller_name is not None
        assert seller_name.text == "Test GmbH"

    def test_xml_contains_buyer_info(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        buyer_name = root.find(
            ".//ram:ApplicableHeaderTradeAgreement/ram:BuyerTradeParty/ram:Name", NS
        )
        assert buyer_name is not None
        assert buyer_name.text == "Acme Corp"

    def test_xml_contains_line_items(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        line_items = root.findall(
            ".//ram:IncludedSupplyChainTradeLineItem", NS
        )
        assert len(line_items) == 1

    def test_xml_contains_monetary_totals(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        grand_total = root.find(
            ".//ram:SpecifiedTradeSettlementHeaderMonetarySummation"
            "/ram:GrandTotalAmount", NS
        )
        assert grand_total is not None
        assert "1190" in grand_total.text

    def test_xml_contains_tax_info(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        tax_entries = root.findall(
            ".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax", NS
        )
        assert len(tax_entries) == 1

    def test_xml_contains_payment_means(self, tenant, invoice_record):
        """Bank details should result in SEPA payment means."""
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        payment_means = root.findall(
            ".//ram:SpecifiedTradeSettlementPaymentMeans", NS
        )
        assert len(payment_means) >= 1

    def test_xml_contains_invoice_note(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        notes = root.findall(
            ".//rsm:ExchangedDocument/ram:IncludedNote/ram:Content", NS
        )
        note_texts = [n.text for n in notes]
        assert any("Zahlungsziel" in t for t in note_texts)

    def test_xml_currency_matches_tenant(self, tenant, invoice_record):
        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(invoice_record)
        root = ET.fromstring(xml_bytes)

        currency = root.find(
            ".//ram:ApplicableHeaderTradeSettlement/ram:InvoiceCurrencyCode", NS
        )
        assert currency is not None
        assert currency.text == "EUR"


class TestZugferdXmlFromInvoiceData:
    """Test XML generation from InvoiceData dataclass."""

    def test_generates_xml_from_invoice_data(self, tenant, legal_data):
        from apps.invoices.types import InvoiceData, InvoiceLineItem

        invoice_data = InvoiceData(
            contract_id=1,
            contract_name="Test Contract",
            customer_id=1,
            customer_name="Test Customer",
            customer_address={"street": "Test St", "city": "Berlin", "zip": "10115"},
            billing_date=date(2026, 2, 1),
            billing_period_start=date(2026, 2, 1),
            billing_period_end=date(2026, 2, 28),
            line_items=[
                InvoiceLineItem(
                    item_id=1,
                    product_name="Test Product",
                    description="Test",
                    quantity=2,
                    unit_price=Decimal("500.00"),
                    amount=Decimal("1000.00"),
                ),
            ],
            invoice_text="Test note",
        )

        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_invoice_data(
            invoice_data=invoice_data,
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("190.00"),
            total_gross=Decimal("1190.00"),
            company=legal_data.to_snapshot(),
        )

        assert xml_bytes is not None
        root = ET.fromstring(xml_bytes)
        assert root.tag.endswith("CrossIndustryInvoice")


class TestZugferdWithoutOptionalData:
    """Test ZUGFeRD generation when optional data is missing."""

    def test_xml_without_bank_details(self, db, tenant, customer, active_contract):
        legal = CompanyLegalData.objects.create(
            tenant=tenant,
            company_name="NoBankDetails GmbH",
            street="Str 1",
            zip_code="12345",
            city="Berlin",
            vat_id="DE999999999",
            commercial_register_court="AG Berlin",
            commercial_register_number="HRB 99999",
            managing_directors=["Test Person"],
            default_tax_rate=Decimal("19.00"),
        )

        record = InvoiceRecord.objects.create(
            tenant=tenant,
            contract=active_contract,
            customer=customer,
            invoice_number="2026-0002",
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("500.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("95.00"),
            total_gross=Decimal("595.00"),
            line_items_snapshot=[
                {
                    "item_id": 1,
                    "product_name": "Service",
                    "description": "",
                    "quantity": 1,
                    "unit_price": "500.00",
                    "amount": "500.00",
                }
            ],
            company_data_snapshot=legal.to_snapshot(),
            status=InvoiceRecord.Status.FINALIZED,
            customer_name="Acme Corp",
            contract_name="Contract",
        )

        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(record)
        assert xml_bytes is not None

        root = ET.fromstring(xml_bytes)
        # No payment means expected
        payment_means = root.findall(
            ".//ram:SpecifiedTradeSettlementPaymentMeans", NS
        )
        assert len(payment_means) == 0

    def test_xml_with_empty_customer_address(self, db, tenant, active_contract):
        legal = CompanyLegalData.objects.create(
            tenant=tenant,
            company_name="Test GmbH",
            street="Str 1",
            zip_code="12345",
            city="München",
            vat_id="DE123456789",
            commercial_register_court="AG München",
            commercial_register_number="HRB 12345",
            managing_directors=["Person"],
            default_tax_rate=Decimal("19.00"),
        )

        cust = Customer.objects.create(
            tenant=tenant,
            name="No Address Co",
            address={},
            is_active=True,
        )

        record = InvoiceRecord.objects.create(
            tenant=tenant,
            contract=active_contract,
            customer=cust,
            invoice_number="2026-0003",
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("19.00"),
            total_gross=Decimal("119.00"),
            line_items_snapshot=[
                {
                    "item_id": 1,
                    "product_name": "Item",
                    "description": "",
                    "quantity": 1,
                    "unit_price": "100.00",
                    "amount": "100.00",
                }
            ],
            company_data_snapshot=legal.to_snapshot(),
            status=InvoiceRecord.Status.FINALIZED,
            customer_name="No Address Co",
            contract_name="Contract",
        )

        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(record)
        assert xml_bytes is not None

        root = ET.fromstring(xml_bytes)
        buyer_name = root.find(
            ".//ram:ApplicableHeaderTradeAgreement/ram:BuyerTradeParty/ram:Name", NS
        )
        assert buyer_name is not None
        assert buyer_name.text == "No Address Co"


class TestMultipleLineItems:
    """Test XML generation with multiple line items."""

    def test_multiple_items(self, db, tenant, customer, active_contract, legal_data):
        record = InvoiceRecord.objects.create(
            tenant=tenant,
            contract=active_contract,
            customer=customer,
            invoice_number="2026-0004",
            billing_date=date(2026, 2, 1),
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            total_net=Decimal("2500.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("475.00"),
            total_gross=Decimal("2975.00"),
            line_items_snapshot=[
                {
                    "item_id": 1,
                    "product_name": "License A",
                    "description": "Standard",
                    "quantity": 5,
                    "unit_price": "200.00",
                    "amount": "1000.00",
                },
                {
                    "item_id": 2,
                    "product_name": "License B",
                    "description": "Premium",
                    "quantity": 3,
                    "unit_price": "500.00",
                    "amount": "1500.00",
                },
            ],
            company_data_snapshot=legal_data.to_snapshot(),
            status=InvoiceRecord.Status.FINALIZED,
            customer_name="Acme Corp",
            contract_name="Multi Contract",
        )

        service = ZugferdService(tenant)
        xml_bytes = service.generate_xml_from_record(record)
        root = ET.fromstring(xml_bytes)

        line_items = root.findall(
            ".//ram:IncludedSupplyChainTradeLineItem", NS
        )
        assert len(line_items) == 2


class TestZugferdTenantSettings:
    """Test the ZUGFeRD tenant settings."""

    def test_default_setting_is_false(self, tenant):
        assert tenant.settings.get("zugferd_default", False) is False

    def test_enable_zugferd_default(self, tenant):
        tenant.settings["zugferd_default"] = True
        tenant.save()
        tenant.refresh_from_db()
        assert tenant.settings["zugferd_default"] is True

    def test_disable_zugferd_default(self, tenant):
        tenant.settings["zugferd_default"] = True
        tenant.save()
        tenant.settings["zugferd_default"] = False
        tenant.save()
        tenant.refresh_from_db()
        assert tenant.settings["zugferd_default"] is False
