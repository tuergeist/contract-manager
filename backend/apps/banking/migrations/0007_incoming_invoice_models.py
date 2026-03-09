"""Add InvoiceInbox and IncomingInvoice models."""

import uuid
import django.db.models.deletion
from django.db import migrations, models
import apps.banking.models


class Migration(migrations.Migration):

    dependencies = [
        ("banking", "0006_imported_invoice"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InvoiceInbox",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(help_text="User-given label for this inbox", max_length=255)),
                ("inbox_type", models.CharField(choices=[("imap", "IMAP"), ("m365", "Microsoft 365")], default="imap", max_length=10)),
                ("host", models.CharField(blank=True, max_length=255)),
                ("port", models.PositiveIntegerField(default=993)),
                ("username", models.CharField(blank=True, max_length=255)),
                ("password", models.CharField(blank=True, help_text="Encrypted password", max_length=500)),
                ("folder", models.CharField(default="INBOX", max_length=255)),
                ("use_ssl", models.BooleanField(default=True)),
                ("m365_mailbox", models.CharField(blank=True, help_text="M365 mailbox email address (uses tenant M365 credentials)", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("poll_interval_minutes", models.PositiveIntegerField(default=15)),
                ("last_polled_at", models.DateTimeField(blank=True, null=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.tenant")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="IncomingInvoice",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("supplier_name", models.CharField(blank=True, max_length=255)),
                ("invoice_number", models.CharField(blank=True, max_length=100)),
                ("invoice_date", models.DateField(blank=True, null=True)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("net_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("vat_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("gross_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("pdf_file", models.FileField(upload_to=apps.banking.models.incoming_invoice_upload_path)),
                ("original_filename", models.CharField(max_length=255)),
                ("file_size", models.PositiveIntegerField(default=0)),
                ("extraction_status", models.CharField(choices=[("pending", "Pending"), ("extracting", "Extracting"), ("extracted", "Extracted"), ("extraction_failed", "Extraction Failed"), ("confirmed", "Confirmed"), ("matched", "Matched")], default="pending", max_length=20)),
                ("extraction_error", models.TextField(blank=True)),
                ("email_message_id", models.CharField(blank=True, max_length=500)),
                ("source_email_subject", models.CharField(blank=True, max_length=500)),
                ("source_email_date", models.DateTimeField(blank=True, null=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.tenant")),
                ("inbox", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incoming_invoices", to="banking.invoiceinbox")),
                ("counterparty", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incoming_invoices", to="banking.counterparty")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="incominginvoice",
            constraint=models.UniqueConstraint(
                condition=models.Q(("email_message_id__gt", "")),
                fields=("tenant", "email_message_id", "original_filename"),
                name="unique_incoming_invoice_per_tenant_email",
            ),
        ),
        migrations.AddIndex(
            model_name="incominginvoice",
            index=models.Index(fields=["tenant", "extraction_status"], name="idx_incoming_inv_tenant_status"),
        ),
    ]
