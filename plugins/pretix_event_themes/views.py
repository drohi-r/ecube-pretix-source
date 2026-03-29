from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from pretix.control.permissions import EventPermissionRequiredMixin, OrganizerPermissionRequiredMixin
from pretix.control.views.event import EventSettingsViewMixin

from .forms import EventThemesSettingsForm
from .models import EventDesignAssetPack
from .services.assets import process_event_asset_pack
from .theme_config import (
    PRESET_CHOICES,
    PUBLIC_SUBDIR,
    MEDIA_ROOT,
    canonical_preset,
    normalize_hex_color,
    normalize_overlay,
    preset_to_base_theme,
    public_media_url,
    sanitize_filename,
)


class EventThemesSettingsView(EventPermissionRequiredMixin, EventSettingsViewMixin, View):
    permission = "can_change_event_settings"
    template_name = "pretix_event_themes/event_settings.html"

    def get(self, request, organizer, event, *args, **kwargs):
        form = self._build_form(request)
        resp = render(request, self.template_name, self._context(request, form))
        resp['Content-Security-Policy'] = "style-src 'unsafe-inline' 'self'"
        return resp

    def post(self, request, organizer, event, *args, **kwargs):
        if request.POST.get("remove_background") == "1":
            request.event.settings.set("ecube_bg_url", "")
            request.event.cache.clear()
            messages.success(request, _("Background removed."))
            return redirect(self.get_success_url())

        remove_action = self._handle_asset_remove_action(request)
        if remove_action:
            request.event.cache.clear()
            messages.success(request, remove_action)
            return redirect(self.get_success_url())

        form = self._build_form(request, data=request.POST, files=request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, self._context(request, form), status=400)

        self._save_theme_settings(request, form)
        asset_pack, changed_fields = self._save_asset_pack(request, form)

        uploaded = form.cleaned_data.get("background_image")
        if uploaded:
            self._save_legacy_background(request, uploaded)

        if asset_pack and changed_fields:
            process_event_asset_pack(asset_pack, changed_fields=changed_fields)

        message = _("Theme settings updated.")
        if uploaded:
            message = _("Theme settings and background updated.")
        if asset_pack and changed_fields:
            message = _("Theme settings and design assets updated.")
        if uploaded and asset_pack and changed_fields:
            message = _("Theme settings, design assets, and background updated.")

        messages.success(request, message)

        request.event.cache.clear()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return f"/control/event/{self.request.organizer.slug}/{self.request.event.slug}/settings/themes/"

    def _build_form(self, request, data=None, files=None):
        asset_pack = self._get_asset_pack(request.event)
        initial = {
            "ecube_theme_preset": canonical_preset(request.event.settings.get("ecube_theme_preset", "")),
            "ecube_primary": request.event.settings.get("ecube_primary", ""),
            "ecube_secondary": request.event.settings.get("ecube_secondary", ""),
            "ecube_accent": request.event.settings.get("ecube_accent", ""),
            "ecube_overlay_opacity": request.event.settings.get("ecube_overlay_opacity", ""),
            "ecube_custom_css": request.event.settings.get("ecube_custom_css", ""),
            "hero_focal_x": getattr(asset_pack, "hero_focal_x", 0.50),
            "hero_focal_y": getattr(asset_pack, "hero_focal_y", 0.50),
            "use_hero_in_email": self._setting_bool(request.event, "ecube_use_hero_in_email"),
            "use_hero_on_ticket": self._setting_bool(request.event, "ecube_use_hero_on_ticket"),
        }
        return EventThemesSettingsForm(data=data, files=files, initial=initial, organizer=request.organizer)

    def _context(self, request, form):
        asset_pack = self._get_asset_pack(request.event)
        return {
            "form": form,
            "current_bg_url": request.event.settings.get("ecube_bg_url", ""),
            "asset_pack": asset_pack,
            "hero_preview_url": self._asset_url(asset_pack, "hero_original"),
            "hero_card_16x9_url": self._asset_url(asset_pack, "hero_card_16x9"),
            "hero_email_banner_url": self._asset_url(asset_pack, "hero_email_banner"),
            "hero_ticket_texture_url": self._asset_url(asset_pack, "hero_ticket_texture"),
            "logo_preview_url": self._asset_url(asset_pack, "logo_original"),
            "logo_email_url": self._asset_url(asset_pack, "logo_email"),
            "logo_ticket_url": self._asset_url(asset_pack, "logo_ticket"),
            "background_texture_original_url": self._asset_url(asset_pack, "background_texture_original"),
            "background_texture_web_url": self._asset_url(asset_pack, "background_texture_web"),
            "background_texture_ticket_url": self._asset_url(asset_pack, "background_texture_ticket"),
            "thumbnail_override_url": self._asset_url(asset_pack, "thumbnail_override"),
            "thumbnail_square_url": self._asset_url(asset_pack, "thumbnail_square"),
        }

    def _save_theme_settings(self, request, form):
        selected_preset = canonical_preset(form.cleaned_data.get("ecube_theme_preset", "").strip())
        valid_presets = {k for k, _ in PRESET_CHOICES} | {""}
        if selected_preset in valid_presets:
            request.event.settings.set("ecube_theme_preset", selected_preset)
            request.event.settings.set("ecube_theme", preset_to_base_theme(selected_preset) if selected_preset else "")

        request.event.settings.set("ecube_primary", form.cleaned_data.get("ecube_primary", ""))
        request.event.settings.set("ecube_secondary", form.cleaned_data.get("ecube_secondary", ""))
        request.event.settings.set("ecube_accent", form.cleaned_data.get("ecube_accent", ""))
        request.event.settings.set("ecube_overlay_opacity", form.cleaned_data.get("ecube_overlay_opacity", ""))
        request.event.settings.set("ecube_custom_css", form.cleaned_data.get("ecube_custom_css", ""))
        request.event.settings.set("ecube_use_hero_in_email", bool(form.cleaned_data.get("use_hero_in_email")))
        request.event.settings.set("ecube_use_hero_on_ticket", bool(form.cleaned_data.get("use_hero_on_ticket")))

    def _save_asset_pack(self, request, form):
        uploads = {
            "hero_original": form.cleaned_data.get("hero_image"),
            "logo_original": form.cleaned_data.get("logo_image"),
            "background_texture_original": form.cleaned_data.get("background_texture_image"),
            "thumbnail_override": form.cleaned_data.get("thumbnail_override_image"),
        }
        has_file_upload = any(bool(value) for value in uploads.values())
        asset_pack = self._get_asset_pack(request.event)

        if not asset_pack and not has_file_upload:
            return None, set()

        asset_pack = asset_pack or EventDesignAssetPack.objects.create(event=request.event)
        changed_fields = set()

        focal_x = form.cleaned_data.get("hero_focal_x")
        focal_y = form.cleaned_data.get("hero_focal_y")
        if focal_x is not None and asset_pack.hero_focal_x != focal_x:
            asset_pack.hero_focal_x = focal_x
            changed_fields.add("hero_original")
        if focal_y is not None and asset_pack.hero_focal_y != focal_y:
            asset_pack.hero_focal_y = focal_y
            changed_fields.add("hero_original")

        for field_name, uploaded_file in uploads.items():
            if uploaded_file:
                existing = getattr(asset_pack, field_name)
                if getattr(existing, "name", ""):
                    existing.delete(save=False)
                setattr(asset_pack, field_name, uploaded_file)
                changed_fields.add(field_name)

        if changed_fields:
            asset_pack.save()
        return asset_pack, changed_fields

    def _handle_asset_remove_action(self, request):
        actions = {
            "remove_hero_image": ("hero_original", _("Hero image removed.")),
            "remove_logo_image": ("logo_original", _("Logo image removed.")),
            "remove_background_texture": ("background_texture_original", _("Background texture removed.")),
            "remove_thumbnail_override": ("thumbnail_override", _("Thumbnail override removed.")),
        }
        for trigger, payload in actions.items():
            if request.POST.get(trigger) == "1":
                return self._remove_asset_field(request.event, payload[0], payload[1])
        return None

    def _remove_asset_field(self, event, field_name, success_message):
        asset_pack = self._get_asset_pack(event)
        if not asset_pack:
            return success_message
        field = getattr(asset_pack, field_name)
        if getattr(field, "name", ""):
            field.delete(save=False)
        setattr(asset_pack, field_name, "")
        asset_pack.save(update_fields=[field_name, "updated_at"])
        process_event_asset_pack(asset_pack, changed_fields={field_name})
        return success_message

    def _save_legacy_background(self, request, uploaded):
        target_dir = MEDIA_ROOT / PUBLIC_SUBDIR
        target_dir.mkdir(parents=True, exist_ok=True)

        clean_name = sanitize_filename(uploaded.name)
        final_name = f"{request.event.slug}_{clean_name}"
        target_path = target_dir / final_name

        with open(target_path, "wb+") as output_file:
            for chunk in uploaded.chunks():
                output_file.write(chunk)

        request.event.settings.set("ecube_bg_url", public_media_url(f"{PUBLIC_SUBDIR}/{final_name}"))

    def _asset_url(self, asset_pack, field_name):
        if not asset_pack:
            return ""
        field = getattr(asset_pack, field_name, None)
        if not getattr(field, "name", ""):
            return ""
        try:
            return field.url
        except Exception:
            return ""

    def _setting_bool(self, target, key):
        value = target.settings.get(key, None)
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return False
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def _get_asset_pack(self, event):
        try:
            return event.ecube_design_assets
        except Exception:
            return None


class OrganizerThemesSettingsView(OrganizerPermissionRequiredMixin, View):
    permission = "can_change_organizer_settings"
    template_name = "pretix_event_themes/organizer_settings.html"

    def get(self, request, organizer, *args, **kwargs):
        return render(request, self.template_name, {
            "current_preset": canonical_preset(
                request.organizer.settings.get("ecube_theme_preset", "") or request.organizer.settings.get("ecube_theme", "bg")
            ),
            "preset_choices": PRESET_CHOICES,
            "current_primary": request.organizer.settings.get("ecube_primary", ""),
            "current_secondary": request.organizer.settings.get("ecube_secondary", ""),
            "current_accent": request.organizer.settings.get("ecube_accent", ""),
            "current_overlay": request.organizer.settings.get("ecube_overlay_opacity", ""),
            "current_custom_css": request.organizer.settings.get("ecube_custom_css", ""),
        })

    def post(self, request, organizer, *args, **kwargs):
        selected_preset = request.POST.get("ecube_theme_preset", "gilt").strip()
        selected_preset = canonical_preset(selected_preset)
        valid_presets = {k for k, _ in PRESET_CHOICES}
        if selected_preset not in valid_presets:
            selected_preset = "gilt"

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
