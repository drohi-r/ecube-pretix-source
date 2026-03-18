import os
import re
from pathlib import Path

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from pretix.control.permissions import EventPermissionRequiredMixin, OrganizerPermissionRequiredMixin
from pretix.control.views.event import EventSettingsViewMixin


MEDIA_ROOT = Path("/data/media")
PUBLIC_SUBDIR = "pub/ecube_themes"

PRESET_CHOICES = [
    ("bg", "Black & Gold"),
    ("rb", "Red & Black"),
    ("mb", "Midnight & Electric Blue"),
    ("nobo", "Nobo"),
    ("nexus", "Nexus"),
    ("resonance", "Resonance"),
    ("bhn", "BHN"),
]

EVENT_PRESET_CHOICES = [
    ("", "Use organizer default"),
] + PRESET_CHOICES

BASE_THEME_FOR_PRESET = {
    "bg": "bg",
    "rb": "rb",
    "mb": "mb",
    "nobo": "bg",
    "nexus": "mb",
    "resonance": "rb",
    "bhn": "rb",
}


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = name.replace(" ", "_")
    name = re.sub(r"[()]+", "", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name


def preset_label(value: str) -> str:
    mapping = dict(PRESET_CHOICES)
    return mapping.get(value or "bg", "Black & Gold")


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


def preset_to_base_theme(value: str) -> str:
    return BASE_THEME_FOR_PRESET.get(value or "", "bg")


class EventThemesSettingsView(EventPermissionRequiredMixin, EventSettingsViewMixin, View):
    permission = "can_change_event_settings"
    template_name = "pretix_event_themes/event_settings.html"

    def get(self, request, organizer, event, *args, **kwargs):
        org_preset = request.organizer.settings.get("ecube_theme_preset", "") or request.organizer.settings.get("ecube_theme", "bg")
        preset_choices = [(v, l) for v, l in EVENT_PRESET_CHOICES]
        preset_choices[0] = ("", f"Use organizer default ({preset_label(org_preset)})")

        return render(request, self.template_name, {
            "current_preset": request.event.settings.get("ecube_theme_preset", ""),
            "preset_choices": preset_choices,
            "current_bg_url": request.event.settings.get("ecube_bg_url", ""),
            "current_primary": request.event.settings.get("ecube_primary", ""),
            "current_secondary": request.event.settings.get("ecube_secondary", ""),
            "current_accent": request.event.settings.get("ecube_accent", ""),
            "current_overlay": request.event.settings.get("ecube_overlay_opacity", ""),
            "current_custom_css": request.event.settings.get("ecube_custom_css", ""),
        })

    def post(self, request, organizer, event, *args, **kwargs):
        if request.POST.get("remove_background") == "1":
            request.event.settings.set("ecube_bg_url", "")
            request.event.cache.clear()
            messages.success(request, _("Background removed."))
            return redirect(self.get_success_url())

        selected_preset = request.POST.get("ecube_theme_preset", "").strip()
        if selected_preset in ("", "bg", "rb", "mb", "nobo", "nexus", "resonance", "bhn"):
            request.event.settings.set("ecube_theme_preset", selected_preset)
            if selected_preset:
                request.event.settings.set("ecube_theme", preset_to_base_theme(selected_preset))
            else:
                request.event.settings.set("ecube_theme", "")

        primary = normalize_hex_color(request.POST.get("ecube_primary", ""))
        secondary = normalize_hex_color(request.POST.get("ecube_secondary", ""))
        accent = normalize_hex_color(request.POST.get("ecube_accent", ""))
        overlay = normalize_overlay(request.POST.get("ecube_overlay_opacity", ""))
        custom_css = request.POST.get("ecube_custom_css", "")

        request.event.settings.set("ecube_primary", primary)
        request.event.settings.set("ecube_secondary", secondary)
        request.event.settings.set("ecube_accent", accent)
        request.event.settings.set("ecube_overlay_opacity", overlay)
        request.event.settings.set("ecube_custom_css", custom_css)

        uploaded = request.FILES.get("background_image")
        if uploaded:
            target_dir = MEDIA_ROOT / PUBLIC_SUBDIR
            target_dir.mkdir(parents=True, exist_ok=True)

            clean_name = sanitize_filename(uploaded.name)
            final_name = f"{request.event.slug}_{clean_name}"
            target_path = target_dir / final_name

            with open(target_path, "wb+") as f:
                for chunk in uploaded.chunks():
                    f.write(chunk)

            public_url = f"/media/{PUBLIC_SUBDIR}/{final_name}"
            request.event.settings.set("ecube_bg_url", public_url)
            messages.success(request, _("Theme settings and background updated."))
        else:
            messages.success(request, _("Theme settings updated."))

        request.event.cache.clear()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return f"/control/event/{self.request.organizer.slug}/{self.request.event.slug}/settings/themes/"


class OrganizerThemesSettingsView(OrganizerPermissionRequiredMixin, View):
    permission = "can_change_organizer_settings"
    template_name = "pretix_event_themes/organizer_settings.html"

    def get(self, request, organizer, *args, **kwargs):
        return render(request, self.template_name, {
            "current_preset": request.organizer.settings.get("ecube_theme_preset", "") or request.organizer.settings.get("ecube_theme", "bg"),
            "preset_choices": PRESET_CHOICES,
            "current_primary": request.organizer.settings.get("ecube_primary", ""),
            "current_secondary": request.organizer.settings.get("ecube_secondary", ""),
            "current_accent": request.organizer.settings.get("ecube_accent", ""),
            "current_overlay": request.organizer.settings.get("ecube_overlay_opacity", ""),
            "current_custom_css": request.organizer.settings.get("ecube_custom_css", ""),
        })

    def post(self, request, organizer, *args, **kwargs):
        selected_preset = request.POST.get("ecube_theme_preset", "bg").strip()
        if selected_preset not in ("bg", "rb", "mb", "nobo", "nexus", "resonance", "bhn"):
            selected_preset = "bg"

        primary = normalize_hex_color(request.POST.get("ecube_primary", ""))
        secondary = normalize_hex_color(request.POST.get("ecube_secondary", ""))
        accent = normalize_hex_color(request.POST.get("ecube_accent", ""))
        overlay = normalize_overlay(request.POST.get("ecube_overlay_opacity", ""))
        custom_css = request.POST.get("ecube_custom_css", "")

        request.organizer.settings.set("ecube_theme_preset", selected_preset)
        request.organizer.settings.set("ecube_theme", preset_to_base_theme(selected_preset))
        request.organizer.settings.set("ecube_primary", primary)
        request.organizer.settings.set("ecube_secondary", secondary)
        request.organizer.settings.set("ecube_accent", accent)
        request.organizer.settings.set("ecube_overlay_opacity", overlay)
        request.organizer.settings.set("ecube_custom_css", custom_css)

        request.organizer.cache.clear()
        messages.success(request, _("Organizer theme defaults updated."))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return f"/control/organizer/{self.request.organizer.slug}/settings/themes/"