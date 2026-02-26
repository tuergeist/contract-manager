"""Data migration: update existing German VAT sentence defaults to English."""
from django.db import migrations

OLD_EU = "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge gem. § 13b UStG)"
NEW_EU = "Reverse Charge – VAT liability transferred to the recipient (§ 13b UStG)"

OLD_NON_EU = "Umsatzsteuer nicht geschuldet gemäß § 3a Abs. 2 UStG"
NEW_NON_EU = "VAT not applicable – place of supply rules (§ 3a(2) UStG)"


def forwards(apps, schema_editor):
    CompanyLegalData = apps.get_model("invoices", "CompanyLegalData")
    CompanyLegalData.objects.filter(vat_text_eu=OLD_EU).update(vat_text_eu=NEW_EU)
    CompanyLegalData.objects.filter(vat_text_non_eu=OLD_NON_EU).update(vat_text_non_eu=NEW_NON_EU)


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0020_english_vat_sentence_defaults"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
