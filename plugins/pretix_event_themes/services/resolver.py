import logging
from dataclasses import dataclass, replace
from urllib.parse import urljoin

from django.conf import settings

logger = logging.getLogger(__name__)

from ..theme_config import PRESET_DEFAULTS, canonical_preset, preset_to_base_theme


@dataclass
class ResolvedDesignProfile:
    profile_slug: str
    page_theme_slug: str
    email_theme_slug: str
    ticket_theme_slug: str
    primary_color: str
    secondary_color: str
    accent_color: str
    text_color: str
    overlay_strength: float
    hero_image_url: str
    hero_card_16x9_url: str
    hero_email_banner_url: str
    hero_ticket_texture_url: str
    thumbnail_url: str
    logo_url: str
    logo_email_url: str
    logo_ticket_url: str
    background_texture_url: str
    background_texture_ticket_url: str
    use_hero_in_email: bool
    use_hero_on_ticket: bool
    ticket_variant: str


def resolve_design_profile(event, item_override=None):
    profile_slug = _resolve_profile_slug(event, item_override)
    profile_slug = canonical_preset(profile_slug)
    defaults = PRESET_DEFAULTS.get(profile_slug, PRESET_DEFAULTS.get("gilt", {}))
    asset_pack = _get_event_asset_pack(event)
    organizer_assets = _get_organizer_asset_pack(event.organizer)

    return ResolvedDesignProfile(
        profile_slug=profile_slug,
        page_theme_slug=_override_value(item_override, "page_theme_slug") or preset_to_base_theme(profile_slug),
        email_theme_slug=_override_value(item_override, "email_theme_slug") or preset_to_base_theme(profile_slug),
        ticket_theme_slug=_override_value(item_override, "ticket_theme_slug") or preset_to_base_theme(profile_slug),
        primary_color=_resolve_color(event, "ecube_primary", item_override, defaults["primary_color"]),
        secondary_color=_resolve_color(event, "ecube_secondary", item_override, defaults["secondary_color"]),
        accent_color=_resolve_color(event, "ecube_accent", item_override, defaults["accent_color"]),
        text_color=_override_value(item_override, "text_color") or defaults["text_color"],
        overlay_strength=_resolve_overlay(event, item_override, defaults["overlay_strength"]),
        hero_image_url=_override_value(item_override, "hero_image_url") or _asset_url(asset_pack, "hero_original"),
        hero_card_16x9_url=_override_value(item_override, "hero_card_16x9_url") or _asset_url(asset_pack, "hero_card_16x9"),
        hero_email_banner_url=_override_value(item_override, "hero_email_banner_url") or _asset_url(asset_pack, "hero_email_banner"),
        hero_ticket_texture_url=_override_value(item_override, "hero_ticket_texture_url") or _asset_url(asset_pack, "hero_ticket_texture"),
        thumbnail_url=_override_value(item_override, "thumbnail_url") or _asset_url(asset_pack, "thumbnail_square"),
        logo_url=_override_value(item_override, "logo_url") or _asset_url(asset_pack, "logo_original"),
        logo_email_url=_override_value(item_override, "logo_email_url") or _asset_url(asset_pack, "logo_email"),
        logo_ticket_url=_override_value(item_override, "logo_ticket_url") or _asset_url(asset_pack, "logo_ticket"),
        background_texture_url=(
            _override_value(item_override, "background_texture_url")
            or _asset_url(asset_pack, "background_texture_web")
            or _asset_url(organizer_assets, "background_texture_web")
            or _asset_url(asset_pack, "hero_card_16x9")
            or event.settings.get("ecube_bg_url", "")
        ),
        background_texture_ticket_url=(
            _override_value(item_override, "background_texture_ticket_url")
            or _asset_url(asset_pack, "background_texture_ticket")
            or _asset_url(organizer_assets, "background_texture_ticket")
            or event.settings.get("ecube_bg_url", "")
        ),
        use_hero_in_email=_resolve_bool(event, "ecube_use_hero_in_email", item_override, False),
        use_hero_on_ticket=_resolve_bool(event, "ecube_use_hero_on_ticket", item_override, False),
        ticket_variant=_override_value(item_override, "ticket_variant") or defaults["ticket_variant"],
    )


def resolve_absolute_design_profile(event, item_override=None, base_url=None):
    profile = resolve_design_profile(event, item_override=item_override)
    return absolutize_design_profile(profile, base_url=base_url)


def absolutize_design_profile(profile, base_url=None):
    return replace(
        profile,
        hero_image_url=absolute_public_url(profile.hero_image_url, base_url=base_url),
        hero_card_16x9_url=absolute_public_url(profile.hero_card_16x9_url, base_url=base_url),
        hero_email_banner_url=absolute_public_url(profile.hero_email_banner_url, base_url=base_url),
        hero_ticket_texture_url=absolute_public_url(profile.hero_ticket_texture_url, base_url=base_url),
        thumbnail_url=absolute_public_url(profile.thumbnail_url, base_url=base_url),
        logo_url=absolute_public_url(profile.logo_url, base_url=base_url),
        logo_email_url=absolute_public_url(profile.logo_email_url, base_url=base_url),
        logo_ticket_url=absolute_public_url(profile.logo_ticket_url, base_url=base_url),
        background_texture_url=absolute_public_url(profile.background_texture_url, base_url=base_url),
        background_texture_ticket_url=absolute_public_url(profile.background_texture_ticket_url, base_url=base_url),
    )


def absolute_public_url(url, base_url=None):
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    root = (base_url or getattr(settings, "SITE_URL", "") or "").rstrip("/") + "/"
    if not root.strip("/"):
        return url
    return urljoin(root, url.lstrip("/"))


def _resolve_profile_slug(event, item_override):
    override_slug = canonical_preset(_override_value(item_override, "profile_slug"))
    if override_slug:
        return override_slug

    event_pack = _get_event_asset_pack(event)
    if event_pack and event_pack.has_any_assets():
        preset = canonical_preset(event.settings.get("ecube_theme_preset", "") or event.settings.get("ecube_theme", ""))
        if preset:
            return preset

    organizer_assets = _get_organizer_asset_pack(event.organizer)
    if organizer_assets:
        preset = canonical_preset(event.organizer.settings.get("ecube_theme_preset", "") or event.organizer.settings.get("ecube_theme", ""))
        if preset:
            return preset

    return canonical_preset(
        event.settings.get("ecube_theme_preset", "")
        or event.organizer.settings.get("ecube_theme_preset", "")
        or event.settings.get("ecube_theme", "")
        or event.organizer.settings.get("ecube_theme", "bg")
    ) or "bg"


def _resolve_color(event, setting_key, item_override, default):
    return (
        _override_value(item_override, setting_key)
        or event.settings.get(setting_key, "")
        or event.organizer.settings.get(setting_key, "")
        or default
    )


def _resolve_overlay(event, item_override, default):
    raw = (
        _override_value(item_override, "overlay_strength")
        or event.settings.get("ecube_overlay_opacity", "")
        or event.organizer.settings.get("ecube_overlay_opacity", "")
    )
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _resolve_bool(event, setting_key, item_override, default):
    override = _override_value(item_override, setting_key)
    if override is not None:
        return bool(override)
    value = event.settings.get(setting_key, None)
    if value in (None, ""):
        value = event.organizer.settings.get(setting_key, None)
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _asset_url(asset_pack, field_name):
    if not asset_pack:
        return ""
    field = getattr(asset_pack, field_name, None)
    if not getattr(field, "name", ""):
        return ""
    try:
        return field.url
    except Exception:
        logger.debug("Could not resolve asset URL for field %s", field_name)
        return ""


def _override_value(item_override, key):
    if not item_override:
        return None
    if isinstance(item_override, dict):
        return item_override.get(key)
    return getattr(item_override, key, None)


def _get_event_asset_pack(event):
    try:
        return event.ecube_design_assets
    except Exception:
        logger.debug("No design asset pack for event %s", getattr(event, "slug", event))
        return None


def _get_organizer_asset_pack(organizer):
    # TODO: Add organizer-level design asset packs in Phase 2.
    try:
        return organizer.ecube_design_assets
    except Exception:
        logger.debug("No design asset pack for organizer %s", getattr(organizer, "slug", organizer))
        return None
