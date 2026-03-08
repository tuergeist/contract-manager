from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0008_webhook_event_log"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="clockodo_customer_id",
            field=models.CharField(blank=True, help_text="Linked Clockodo customer ID", max_length=100, null=True),
        ),
    ]
