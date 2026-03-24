import uuid
from pathlib import Path

from django.db import models
from pretix.base.models import Event

from .theme_config import sanitize_filename


def event_asset_upload_to(asset_kind):
    def _upload_to(instance, filename):
        organizer_slug = getattr(instance.event.organizer, "slug", "organizer")
        event_slug = getattr(instance.event, "slug", "event")
        ext = Path(filename or "").suffix.lower()
        unique = uuid.uuid4().hex[:12]
        clean_name = sanitize_filename(Path(filename or "asset").stem)
        final_name = f"{clean_name}-{unique}{ext or '.bin'}"
        return "/".join([
            "plugins",
            "pretix_event_themes",
            organizer_slug,
            event_slug,
            asset_kind,
            final_name,
        ])

    return _upload_to


class EventDesignAssetPack(models.Model):
    event = models.OneToOneField(
        Event,
        related_name="ecube_design_assets",
        on_delete=models.CASCADE,
    )
    hero_original = models.FileField(upload_to=event_asset_upload_to("hero-original"), blank=True)
    hero_card_16x9 = models.FileField(upload_to=event_asset_upload_to("hero-card-16x9"), blank=True)
    hero_email_banner = models.FileField(upload_to=event_asset_upload_to("hero-email-banner"), blank=True)
    hero_ticket_texture = models.FileField(upload_to=event_asset_upload_to("hero-ticket-texture"), blank=True)
    thumbnail_override = models.FileField(upload_to=event_asset_upload_to("thumbnail-override"), blank=True)
    thumbnail_square = models.FileField(upload_to=event_asset_upload_to("thumbnail-square"), blank=True)
    logo_original = models.FileField(upload_to=event_asset_upload_to("logo-original"), blank=True)
    logo_email = models.FileField(upload_to=event_asset_upload_to("logo-email"), blank=True)
    logo_ticket = models.FileField(upload_to=event_asset_upload_to("logo-ticket"), blank=True)
    background_texture_original = models.FileField(upload_to=event_asset_upload_to("background-texture-original"), blank=True)
    background_texture_web = models.FileField(upload_to=event_asset_upload_to("background-texture-web"), blank=True)
    background_texture_ticket = models.FileField(upload_to=event_asset_upload_to("background-texture-ticket"), blank=True)
    hero_focal_x = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    hero_focal_y = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    processing_meta = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("event_id",)

    def __str__(self):
        return f"{self.event.slug} design assets"

    def has_any_assets(self):
        for field_name in (
            "hero_original",
            "thumbnail_override",
            "logo_original",
            "background_texture_original",
            "hero_card_16x9",
            "hero_email_banner",
            "hero_ticket_texture",
            "thumbnail_square",
            "logo_email",
            "logo_ticket",
            "background_texture_web",
            "background_texture_ticket",
        ):
            field = getattr(self, field_name)
            if getattr(field, "name", ""):
                return True
        return False
