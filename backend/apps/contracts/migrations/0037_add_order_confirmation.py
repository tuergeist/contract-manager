"""Add OrderConfirmation and OrderConfirmationNumberScheme models."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.contracts.order_confirmation_models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0036_timetrackingprojectmapping_link_source_autolinkrule_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderConfirmationNumberScheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("pattern", models.CharField(default="AB-{YYYY}-{NNNN}", help_text="Pattern with placeholders: {YYYY}, {YY}, {MM}, {NNN}, {NNNN}, {NNNNN}", max_length=100)),
                ("next_counter", models.PositiveIntegerField(default=1)),
                ("reset_period", models.CharField(choices=[("yearly", "Yearly"), ("monthly", "Monthly"), ("never", "Never")], default="yearly", max_length=10)),
                ("last_reset_year", models.PositiveIntegerField(blank=True, null=True)),
                ("last_reset_month", models.PositiveIntegerField(blank=True, null=True)),
                ("tenant", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="order_confirmation_number_scheme", to="tenants.tenant")),
            ],
            options={
                "verbose_name": "Order Confirmation Number Scheme",
            },
        ),
        migrations.CreateModel(
            name="OrderConfirmation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order_confirmation_number", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Sent")], default="draft", max_length=10)),
                ("personal_message", models.TextField(blank=True, help_text="Optional personal message from the sender")),
                ("include_message_in_pdf", models.BooleanField(default=True, help_text="Include personal message in the PDF document")),
                ("include_message_in_email", models.BooleanField(default=True, help_text="Include personal message in the email body")),
                ("additional_emails", models.JSONField(blank=True, default=list, help_text="Additional email addresses beyond billing contacts")),
                ("language", models.CharField(default="de", help_text="Language for the AB document (de/en)", max_length=5)),
                ("pdf_file", models.FileField(blank=True, null=True, upload_to=apps.contracts.order_confirmation_models.ab_pdf_upload_path)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("sent_to", models.JSONField(blank=True, default=list, help_text="List of email addresses the AB was sent to")),
                ("email_message_id", models.CharField(blank=True, help_text="Microsoft Graph API message ID", max_length=255)),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="order_confirmations", to="contracts.contract")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_order_confirmations", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.tenant")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="orderconfirmation",
            index=models.Index(fields=["tenant", "order_confirmation_number"], name="contracts_o_tenant__idx"),
        ),
    ]
