"""Add RBAC: is_system on Role, M2M roles on User."""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0003_add_time_tracking_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="is_system",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="roles",
            field=models.ManyToManyField(
                blank=True,
                related_name="users",
                to="tenants.role",
            ),
        ),
    ]
