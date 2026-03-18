import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from pretix.base.models import Event


class EcubeAccessDoor(models.Model):
    ACTION_ENTRY = "entry"
    ACTION_EXIT = "exit"

    ACTION_CHOICES = (
        (ACTION_ENTRY, "Entry"),
        (ACTION_EXIT, "Exit"),
    )

    event = models.ForeignKey(
        Event,
        related_name="ecube_access_doors",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80)
    public_token = models.CharField(max_length=128, unique=True, db_index=True)
    public_auth_nonce = models.CharField(max_length=64, default="", blank=True)
    access_pin_hash = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    default_action = models.CharField(
        max_length=16,
        choices=ACTION_CHOICES,
        default=ACTION_ENTRY,
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("event", "slug"),)
        ordering = ("name",)

    def __str__(self):
        return f"{self.event.slug} / {self.name}"

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_auth_nonce():
        return secrets.token_urlsafe(24)

    @property
    def has_access_pin(self):
        return bool((self.access_pin_hash or "").strip())

    def set_access_pin(self, raw_pin: str):
        raw_pin = (raw_pin or "").strip()
        if not raw_pin:
            self.access_pin_hash = ""
            return
        self.access_pin_hash = make_password(raw_pin)

    def clear_access_pin(self):
        self.access_pin_hash = ""

    def check_access_pin(self, raw_pin: str) -> bool:
        if not self.has_access_pin:
            return True
        return check_password((raw_pin or "").strip(), self.access_pin_hash)

    def rotate_public_auth_nonce(self):
        self.public_auth_nonce = self.generate_auth_nonce()

    def current_public_auth_session_value(self):
        nonce = (self.public_auth_nonce or "").strip()
        if not nonce:
            nonce = self.generate_auth_nonce()
            self.public_auth_nonce = nonce
        return f"{self.public_token}:{nonce}"


class EcubeAccessScanLog(models.Model):
    ENGINE_PRETIX = "pretix"
    ENGINE_CREDENTIAL = "credential"
    ENGINE_UNKNOWN = "unknown"

    ENGINE_CHOICES = (
        (ENGINE_PRETIX, "Pretix"),
        (ENGINE_CREDENTIAL, "Credential"),
        (ENGINE_UNKNOWN, "Unknown"),
    )

    TYPE_TICKET = "ticket"
    TYPE_CREDENTIAL = "credential"
    TYPE_UNKNOWN = "unknown"

    TYPE_CHOICES = (
        (TYPE_TICKET, "Ticket"),
        (TYPE_CREDENTIAL, "Credential"),
        (TYPE_UNKNOWN, "Unknown"),
    )

    ACTION_ENTRY = "entry"
    ACTION_EXIT = "exit"

    ACTION_CHOICES = (
        (ACTION_ENTRY, "Entry"),
        (ACTION_EXIT, "Exit"),
    )

    RESULT_ALLOWED = "allowed"
    RESULT_ALLOWED_EXIT = "allowed_exit"
    RESULT_DUPLICATE = "duplicate"
    RESULT_REVOKED = "revoked"
    RESULT_BLOCKED = "blocked"
    RESULT_EXPIRED = "expired"
    RESULT_INVALID = "invalid"
    RESULT_NOT_INSIDE = "not_inside"
    RESULT_DENIED = "denied"
    RESULT_ERROR = "error"
    RESULT_PENDING = "pending"

    RESULT_CHOICES = (
        (RESULT_ALLOWED, "Allowed"),
        (RESULT_ALLOWED_EXIT, "Allowed exit"),
        (RESULT_DUPLICATE, "Duplicate"),
        (RESULT_REVOKED, "Revoked"),
        (RESULT_BLOCKED, "Blocked"),
        (RESULT_EXPIRED, "Expired"),
        (RESULT_INVALID, "Invalid"),
        (RESULT_NOT_INSIDE, "Not inside"),
        (RESULT_DENIED, "Denied"),
        (RESULT_ERROR, "Error"),
        (RESULT_PENDING, "Pending"),
    )

    event = models.ForeignKey(
        Event,
        related_name="ecube_access_scan_logs",
        on_delete=models.CASCADE,
    )

    engine = models.CharField(max_length=32, choices=ENGINE_CHOICES, default=ENGINE_UNKNOWN, db_index=True)
    object_type = models.CharField(max_length=32, choices=TYPE_CHOICES, default=TYPE_UNKNOWN, db_index=True)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, default=ACTION_ENTRY, db_index=True)

    raw_payload = models.TextField(blank=True)
    normalized_code = models.CharField(max_length=255, blank=True, db_index=True)

    display_name = models.CharField(max_length=255, blank=True)
    display_type = models.CharField(max_length=255, blank=True)

    result = models.CharField(max_length=32, choices=RESULT_CHOICES, default=RESULT_PENDING, db_index=True)
    message = models.TextField(blank=True)

    gate = models.CharField(max_length=255, blank=True)
    operator_name = models.CharField(max_length=255, blank=True)
    device_id = models.CharField(max_length=255, blank=True)

    response_snapshot = models.JSONField(blank=True, null=True)
    scanned_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-scanned_at",)
        indexes = [
            models.Index(fields=["event", "scanned_at"]),
            models.Index(fields=["event", "engine"]),
            models.Index(fields=["event", "result"]),
            models.Index(fields=["event", "action"]),
        ]

    def __str__(self):
        return f"{self.event.slug} | {self.action} | {self.result} | {self.display_name or self.normalized_code or 'scan'}"

