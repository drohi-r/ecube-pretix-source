import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from pretix.base.models import Event


class AdmissionCredential(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_USED = "used"
    STATUS_BLOCKED = "blocked"
    STATUS_REVOKED = "revoked"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, _("Active")),
        (STATUS_USED, _("Used")),
        (STATUS_BLOCKED, _("Blocked")),
        (STATUS_REVOKED, _("Revoked")),
        (STATUS_EXPIRED, _("Expired")),
    )

    TYPE_GUEST = "guest"
    TYPE_VIP = "vip"
    TYPE_ARTIST = "artist"
    TYPE_STAFF = "staff"
    TYPE_MEDIA = "media"
    TYPE_VENDOR = "vendor"
    TYPE_OTHER = "other"

    TYPE_CHOICES = (
        (TYPE_GUEST, _("Guest")),
        (TYPE_VIP, _("VIP")),
        (TYPE_ARTIST, _("Artist")),
        (TYPE_STAFF, _("Staff")),
        (TYPE_MEDIA, _("Media")),
        (TYPE_VENDOR, _("Vendor")),
        (TYPE_OTHER, _("Other")),
    )

    ENTRY_MODE_SINGLE = "single"
    ENTRY_MODE_REENTRY_AFTER_EXIT = "reentry_after_exit"
    ENTRY_MODE_MULTI = "multi"

    ENTRY_MODE_CHOICES = (
        (ENTRY_MODE_SINGLE, _("Single entry only")),
        (ENTRY_MODE_REENTRY_AFTER_EXIT, _("Re-entry allowed only after exit scan")),
        (ENTRY_MODE_MULTI, _("Multiple entries allowed")),
    )

    event = models.ForeignKey(
        Event,
        related_name="admission_credentials",
        on_delete=models.CASCADE,
    )

    credential_code = models.CharField(max_length=64, db_index=True)
    qr_token = models.CharField(max_length=255, unique=True, db_index=True)

    credential_type = models.CharField(
        max_length=32,
        choices=TYPE_CHOICES,
        default=TYPE_GUEST,
        db_index=True,
    )
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )

    entry_mode = models.CharField(
        max_length=32,
        choices=ENTRY_MODE_CHOICES,
        default=ENTRY_MODE_SINGLE,
        db_index=True,
    )
    is_inside = models.BooleanField(default=False, db_index=True)
    last_entry_at = models.DateTimeField(blank=True, null=True)
    last_exit_at = models.DateTimeField(blank=True, null=True)

    holder_name = models.CharField(max_length=255, db_index=True)
    holder_email = models.EmailField(blank=True)
    holder_phone = models.CharField(max_length=64, blank=True)
    holder_photo = models.ImageField(
        upload_to="admissions_photos/",
        blank=True,
        null=True,
    )

    label = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    valid_from = models.DateTimeField(blank=True, null=True)
    valid_until = models.DateTimeField(blank=True, null=True)

    issued_at = models.DateTimeField(blank=True, null=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="issued_admission_credentials",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    revoked_at = models.DateTimeField(blank=True, null=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="revoked_admission_credentials",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    revocation_reason = models.TextField(blank=True)

    last_scanned_at = models.DateTimeField(blank=True, null=True)
    last_scanned_gate = models.CharField(max_length=255, blank=True)
    scan_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["event", "credential_type"]),
            models.Index(fields=["event", "credential_code"]),
            models.Index(fields=["event", "holder_name"]),
            models.Index(fields=["event", "entry_mode"]),
            models.Index(fields=["event", "is_inside"]),
        ]
        unique_together = (
            ("event", "credential_code"),
        )

    def __str__(self):
        return f"{self.credential_code} — {self.holder_name}"

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)


class AdmissionScanEvent(models.Model):
    ACTION_ENTRY = "entry"
    ACTION_EXIT = "exit"

    ACTION_CHOICES = (
        (ACTION_ENTRY, _("Entry")),
        (ACTION_EXIT, _("Exit")),
    )

    RESULT_ALLOWED = "allowed"
    RESULT_ALLOWED_EXIT = "allowed_exit"
    RESULT_DENIED = "denied"
    RESULT_REVOKED = "revoked"
    RESULT_BLOCKED = "blocked"
    RESULT_EXPIRED = "expired"
    RESULT_DUPLICATE = "duplicate"
    RESULT_INVALID = "invalid"
    RESULT_NOT_INSIDE = "not_inside"
    RESULT_ERROR = "error"

    RESULT_CHOICES = (
        (RESULT_ALLOWED, _("Allowed")),
        (RESULT_ALLOWED_EXIT, _("Allowed exit")),
        (RESULT_DENIED, _("Denied")),
        (RESULT_REVOKED, _("Revoked")),
        (RESULT_BLOCKED, _("Blocked")),
        (RESULT_EXPIRED, _("Expired")),
        (RESULT_DUPLICATE, _("Duplicate")),
        (RESULT_INVALID, _("Invalid")),
        (RESULT_NOT_INSIDE, _("Not inside")),
        (RESULT_ERROR, _("Error")),
    )

    event = models.ForeignKey(
        Event,
        related_name="admission_scan_events",
        on_delete=models.CASCADE,
    )
    credential = models.ForeignKey(
        AdmissionCredential,
        related_name="scan_events",
        on_delete=models.CASCADE,
    )

    action = models.CharField(
        max_length=16,
        choices=ACTION_CHOICES,
        default=ACTION_ENTRY,
        db_index=True,
    )
    scanned_at = models.DateTimeField(default=timezone.now, db_index=True)
    gate = models.CharField(max_length=255, blank=True)
    operator_name = models.CharField(max_length=255, blank=True)
    device_id = models.CharField(max_length=255, blank=True)

    result = models.CharField(max_length=32, choices=RESULT_CHOICES, db_index=True)
    message = models.TextField(blank=True)
    payload_snapshot = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-scanned_at",)
        indexes = [
            models.Index(fields=["event", "scanned_at"]),
            models.Index(fields=["credential", "scanned_at"]),
            models.Index(fields=["result"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.credential.credential_code} @ {self.scanned_at} [{self.action}/{self.result}]"

