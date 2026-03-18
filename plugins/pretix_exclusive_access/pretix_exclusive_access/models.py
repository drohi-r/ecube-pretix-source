# v1.1 additions

GUEST_CATEGORY_CHOICES = [
    ("vip", "VIP"),
    ("influencer", "Influencer"),
    ("press", "Press"),
    ("artist_guest", "Artist Guest"),
    ("partner", "Partner"),
    ("internal", "Internal"),
    ("general_guest", "General Guest"),
    ("other", "Other"),
]

SOURCE_CHOICES = [
    ("public_form", "Public Form"),
    ("manual_admin", "Manual Admin Entry"),
    ("import", "Imported"),
    ("partner", "Partner Submission"),
]

GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
]
import hashlib
import os
import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from pretix.base.models import Event, Item
from pretix.base.models.orders import OrderPosition


def application_photo_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return (
        f"exclusive_access/{instance.event.organizer.slug}/"
        f"{instance.event.slug}/{timezone.now():%Y/%m}/"
        f"{uuid.uuid4().hex}{ext}"
    )


class ApplicationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class ExclusiveAccessApplication(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="exclusive_access_applications",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="exclusive_access_applications",
    )

    full_name = models.CharField(max_length=190)
    gender = models.CharField(
        max_length=16,
        choices=GENDER_CHOICES,
        blank=True,
        default="",
        db_index=True,
    )
    email = models.EmailField()
    phone = models.CharField(
        max_length=50,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r"^[0-9+\-\s()]+$",
                message=_("Enter a valid phone number."),
            )
        ],
    )
    instagram_handle = models.CharField(max_length=255, blank=True, default="")
    referred_by = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    photo = models.ImageField(upload_to=application_photo_upload_to, blank=True)
    photo_uploaded_at = models.DateTimeField(auto_now_add=True)
    photo_hash = models.CharField(max_length=64, blank=True)
    identity_photo_locked = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        db_index=True,
    )

    voucher_code = models.CharField(max_length=120, blank=True)
    voucher_id = models.PositiveIntegerField(null=True, blank=True)

    access_token = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    access_token_created_at = models.DateTimeField(null=True, blank=True)

    approved_order_code = models.CharField(max_length=32, blank=True)
    approved_order_position = models.ForeignKey(
        OrderPosition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="exclusive_access_application",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    # --- v1.1 fields ---

    guest_category = models.CharField(
        max_length=32,
        choices=GUEST_CATEGORY_CHOICES,
        blank=True,
        null=True,
        db_index=True
    )

    status_reason = models.TextField(
        blank=True,
        default=""
    )

    internal_note = models.TextField(
        blank=True,
        default=""
    )

    source = models.CharField(
        max_length=32,
        choices=SOURCE_CHOICES,
        default="public_form",
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_exclusive_access_applications",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = (("event", "email"),)
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["event", "email"]),
            models.Index(fields=["event", "access_token"]),
        ]

    def save(self, *args, **kwargs):
        if self.photo and not self.photo_hash:
            try:
                hasher = hashlib.sha256()
                for chunk in self.photo.file.chunks():
                    hasher.update(chunk)
                self.photo_hash = hasher.hexdigest()
                self.photo.file.seek(0)
            except Exception:
                pass
        super().save(*args, **kwargs)

