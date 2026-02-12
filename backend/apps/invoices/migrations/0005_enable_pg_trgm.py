"""Enable pg_trgm extension for fuzzy text matching."""

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0004_imported_invoice"),
    ]

    operations = [
        TrigramExtension(),
    ]
