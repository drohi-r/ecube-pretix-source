from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

from .theme_config import EVENT_PRESET_CHOICES, normalize_hex_color, normalize_overlay


class EventThemesSettingsForm(forms.Form):
    ecube_theme_preset = forms.ChoiceField(choices=EVENT_PRESET_CHOICES)
    ecube_primary = forms.CharField(required=False)
    ecube_secondary = forms.CharField(required=False)
    ecube_accent = forms.CharField(required=False)
    ecube_overlay_opacity = forms.CharField(required=False)
    ecube_custom_css = forms.CharField(required=False, widget=forms.Textarea)

    background_image = forms.FileField(required=False)
    hero_image = forms.FileField(required=False)
    logo_image = forms.FileField(required=False)
    background_texture_image = forms.FileField(required=False)
    thumbnail_override_image = forms.FileField(required=False)

    hero_focal_x = forms.DecimalField(required=False, min_value=Decimal("0.00"), max_value=Decimal("1.00"), decimal_places=2)
    hero_focal_y = forms.DecimalField(required=False, min_value=Decimal("0.00"), max_value=Decimal("1.00"), decimal_places=2)
    use_hero_in_email = forms.BooleanField(required=False)
    use_hero_on_ticket = forms.BooleanField(required=False)

    def __init__(self, *args, organizer=None, **kwargs):
        self.organizer = organizer
        super().__init__(*args, **kwargs)

        org_label = "Black & Gold"
        if self.organizer is not None:
            from .theme_config import preset_label

            org_preset = self.organizer.settings.get("ecube_theme_preset", "") or self.organizer.settings.get("ecube_theme", "bg")
            org_label = preset_label(org_preset)

        self.fields["ecube_theme_preset"].choices = [
            ("", _("Use organizer default ({label})").format(label=org_label))
        ] + list(EVENT_PRESET_CHOICES[1:])

        text_widgets = {
            "ecube_primary": {"class": "form-control", "placeholder": "#C8000A"},
            "ecube_secondary": {"class": "form-control", "placeholder": "#080808"},
            "ecube_accent": {"class": "form-control", "placeholder": "#F0EDE8"},
            "ecube_overlay_opacity": {"class": "form-control", "placeholder": "0.58"},
            "hero_focal_x": {"class": "form-control", "placeholder": "0.50", "step": "0.01", "min": "0", "max": "1"},
            "hero_focal_y": {"class": "form-control", "placeholder": "0.50", "step": "0.01", "min": "0", "max": "1"},
        }
        for name, attrs in text_widgets.items():
            self.fields[name].widget.attrs.update(attrs)

        self.fields["ecube_theme_preset"].widget.attrs["class"] = "form-control"
        self.fields["ecube_custom_css"].widget.attrs.update({
            "class": "form-control",
            "rows": 12,
            "style": "font-family: monospace;",
        })
        for name in ("background_image", "hero_image", "logo_image", "background_texture_image", "thumbnail_override_image"):
            self.fields[name].widget.attrs.update({"class": "form-control", "accept": "image/*"})

    def clean_ecube_primary(self):
        return normalize_hex_color(self.cleaned_data.get("ecube_primary", ""))

    def clean_ecube_secondary(self):
        return normalize_hex_color(self.cleaned_data.get("ecube_secondary", ""))

    def clean_ecube_accent(self):
        return normalize_hex_color(self.cleaned_data.get("ecube_accent", ""))

    def clean_ecube_overlay_opacity(self):
        return normalize_overlay(self.cleaned_data.get("ecube_overlay_opacity", ""))
