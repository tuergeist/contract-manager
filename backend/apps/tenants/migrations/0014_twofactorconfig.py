"""Add TwoFactorConfig model."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0013_user_dashboard_preferences"),
    ]

    operations = [
        migrations.CreateModel(
            name="TwoFactorConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("method", models.CharField(choices=[("totp", "Authenticator App"), ("email", "Email Code")], max_length=10)),
                ("totp_secret_encrypted", models.TextField(blank=True, default="")),
                ("recovery_codes_hashed", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=False)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="two_factor_config", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
