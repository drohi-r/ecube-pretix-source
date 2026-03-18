from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pretixbase", "0297_outgoingmail"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdmissionCredential",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credential_code", models.CharField(db_index=True, max_length=64)),
                ("qr_token", models.CharField(db_index=True, max_length=255, unique=True)),
                ("credential_type", models.CharField(choices=[("guest", "Guest"), ("vip", "VIP"), ("artist", "Artist"), ("staff", "Staff"), ("media", "Media"), ("vendor", "Vendor"), ("other", "Other")], db_index=True, default="guest", max_length=32)),
                ("status", models.CharField(choices=[("active", "Active"), ("used", "Used"), ("blocked", "Blocked"), ("revoked", "Revoked"), ("expired", "Expired")], db_index=True, default="active", max_length=32)),
                ("holder_name", models.CharField(db_index=True, max_length=255)),
                ("holder_email", models.EmailField(blank=True, max_length=254)),
                ("holder_phone", models.CharField(blank=True, max_length=64)),
                ("holder_photo", models.ImageField(blank=True, null=True, upload_to="admissions_photos/")),
                ("label", models.CharField(blank=True, max_length=255)),
                ("notes", models.TextField(blank=True)),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revocation_reason", models.TextField(blank=True)),
                ("last_scanned_at", models.DateTimeField(blank=True, null=True)),
                ("last_scanned_gate", models.CharField(blank=True, max_length=255)),
                ("scan_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="admission_credentials", to="pretixbase.event")),
                ("issued_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="issued_admission_credentials", to=settings.AUTH_USER_MODEL)),
                ("revoked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="revoked_admission_credentials", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-created_at",),
                "unique_together": {("event", "credential_code")},
            },
        ),
        migrations.CreateModel(
            name="AdmissionScanEvent",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scanned_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("gate", models.CharField(blank=True, max_length=255)),
                ("operator_name", models.CharField(blank=True, max_length=255)),
                ("device_id", models.CharField(blank=True, max_length=255)),
                ("result", models.CharField(choices=[("allowed", "Allowed"), ("denied", "Denied"), ("revoked", "Revoked"), ("blocked", "Blocked"), ("expired", "Expired"), ("duplicate", "Duplicate"), ("invalid", "Invalid"), ("error", "Error")], db_index=True, max_length=32)),
                ("message", models.TextField(blank=True)),
                ("payload_snapshot", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("credential", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scan_events", to="pretix_admissions.admissioncredential")),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="admission_scan_events", to="pretixbase.event")),
            ],
            options={
                "ordering": ("-scanned_at",),
            },
        ),
        migrations.AddIndex(
            model_name="admissioncredential",
            index=models.Index(fields=["event", "status"], name="pretix_admi_event_s_80c6f5_idx"),
        ),
        migrations.AddIndex(
            model_name="admissioncredential",
            index=models.Index(fields=["event", "credential_type"], name="pretix_admi_event_c_9cb0ec_idx"),
        ),
        migrations.AddIndex(
            model_name="admissioncredential",
            index=models.Index(fields=["event", "credential_code"], name="pretix_admi_event_c_d628d2_idx"),
        ),
        migrations.AddIndex(
            model_name="admissioncredential",
            index=models.Index(fields=["event", "holder_name"], name="pretix_admi_event_h_f4d8f2_idx"),
        ),
        migrations.AddIndex(
            model_name="admissionscanevent",
            index=models.Index(fields=["event", "scanned_at"], name="pretix_admi_event_s_414839_idx"),
        ),
        migrations.AddIndex(
            model_name="admissionscanevent",
            index=models.Index(fields=["credential", "scanned_at"], name="pretix_admi_credent_68e270_idx"),
        ),
        migrations.AddIndex(
            model_name="admissionscanevent",
            index=models.Index(fields=["result"], name="pretix_admi_result_4ad16a_idx"),
        ),
    ]

