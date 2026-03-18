from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("pretix_ecube_access", "0003_ecubeaccessdoor"),
    ]

    operations = [
        migrations.AddField(
            model_name="ecubeaccessdoor",
            name="access_pin_hash",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="ecubeaccessdoor",
            name="public_auth_nonce",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
