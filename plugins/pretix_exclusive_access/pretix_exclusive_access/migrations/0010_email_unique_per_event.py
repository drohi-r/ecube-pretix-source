from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pretix_exclusive_access", "0003_exclusiveaccessapplication_guest_category_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="exclusiveaccessapplication",
            unique_together={("event", "email")},
        ),
    ]

