from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pretix_exclusive_access", "0010_email_unique_per_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="exclusiveaccessapplication",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[
                    ("male", "Male"),
                    ("female", "Female"),
                ],
                db_index=True,
                default="",
                max_length=16,
            ),
        ),
    ]
