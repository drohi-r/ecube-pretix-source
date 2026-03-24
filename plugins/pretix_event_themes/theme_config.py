import os
import re
from pathlib import Path

from django.conf import settings


MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT", "/data/media"))
MEDIA_URL = getattr(settings, "MEDIA_URL", "/media/")
PUBLIC_SUBDIR = "pub/ecube_themes"

PRESET_CHOICES = [
    ("bg", "Black & Gold"),
    ("rb", "Red & Black"),
    ("mb", "Midnight & Electric Blue"),
    ("nobo", "Nobo"),
    ("ecube", "Ecube"),
    ("resonance", "Resonance"),
    ("bhn", "BHN"),
    ("aurora", "Aurora"),
    ("ember", "Ember"),
    ("specter", "Specter"),
]

EVENT_PRESET_CHOICES = [
    ("", "Use organizer default"),
] + PRESET_CHOICES

BASE_THEME_FOR_PRESET = {
    "bg": "bg",
    "rb": "rb",
    "mb": "mb",
    "nobo": "bg",
    "ecube": "ecube",
    "nexus": "ecube",
    "resonance": "rb",
    "bhn": "rb",
    "aurora": "aurora",
    "ember": "ember",
    "specter": "specter",
}

LEGACY_PRESET_ALIASES = {
    # Keep nexus as a backward-compatible alias only. It should not appear as
    # a distinct visible preset in new settings UI choices.
    "nexus": "ecube",
}

PRESET_DEFAULTS = {
    "bg": {
        "primary_color": "#C8A64A",
        "secondary_color": "#080808",
        "accent_color": "#F0EDE8",
        "text_color": "#F7F2E7",
        "overlay_strength": 0.58,
        "ticket_variant": "standard",
    },
    "rb": {
        "primary_color": "#C8000A",
        "secondary_color": "#080808",
        "accent_color": "#F4E7E9",
        "text_color": "#F7F3F4",
        "overlay_strength": 0.60,
        "ticket_variant": "contrast",
    },
    "mb": {
        "primary_color": "#0BA7FF",
        "secondary_color": "#040A14",
        "accent_color": "#D6F0FF",
        "text_color": "#F1F8FF",
        "overlay_strength": 0.54,
        "ticket_variant": "neon",
    },
    "nobo": {
        "primary_color": "#D8C08A",
        "secondary_color": "#111111",
        "accent_color": "#F8F1E5",
        "text_color": "#FBF7F0",
        "overlay_strength": 0.50,
        "ticket_variant": "minimal",
    },
    "ecube": {
        "primary_color": "#07B6FF",
        "secondary_color": "#07111D",
        "accent_color": "#C9F4FF",
        "text_color": "#F2FBFF",
        "overlay_strength": 0.48,
        "ticket_variant": "split",
    },
    "resonance": {
        "primary_color": "#FF5A36",
        "secondary_color": "#120B16",
        "accent_color": "#FFE6DE",
        "text_color": "#FFF7F4",
        "overlay_strength": 0.57,
        "ticket_variant": "pulse",
    },
    "bhn": {
        "primary_color": "#D4A93E",
        "secondary_color": "#130F0A",
        "accent_color": "#F5E7C6",
        "text_color": "#FFF8EB",
        "overlay_strength": 0.62,
        "ticket_variant": "headline",
    },
    "aurora": {
        "primary_color": "#7C3AED",
        "secondary_color": "#080612",
        "accent_color": "#E9DDFF",
        "text_color": "#F7F3FF",
        "overlay_strength": 0.44,
        "ticket_variant": "aurora",
    },
    "ember": {
        "primary_color": "#F15B2A",
        "secondary_color": "#140C09",
        "accent_color": "#FFE2D5",
        "text_color": "#FFF7F3",
        "overlay_strength": 0.52,
        "ticket_variant": "warm",
    },
    "specter": {
        "primary_color": "#14B8A6",
        "secondary_color": "#020F0F",
        "accent_color": "#99F6E4",
        "text_color": "#F0FDFA",
        "overlay_strength": 0.56,
        "ticket_variant": "specter",
    },
}


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name or "")
    name = name.replace(" ", "_")
    name = re.sub(r"[()]+", "", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or "asset"


def normalize_hex_color(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith("#"):
        value = "#" + value
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        return value.upper()
    return ""


def normalize_overlay(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        f = float(value)
    except Exception:
        return ""
    f = max(0.0, min(1.0, f))
    return f"{f:.2f}"


def canonical_preset(value: str) -> str:
    return LEGACY_PRESET_ALIASES.get(value or "", value or "")


def preset_to_base_theme(value: str) -> str:
    value = canonical_preset(value)
    return BASE_THEME_FOR_PRESET.get(value, "bg")


def preset_label(value: str) -> str:
    mapping = dict(PRESET_CHOICES)
    value = canonical_preset(value or "bg")
    return mapping.get(value, "Black & Gold")


def public_media_url(path: str) -> str:
    base = MEDIA_URL.rstrip("/")
    return f"{base}/{path.lstrip('/')}"
