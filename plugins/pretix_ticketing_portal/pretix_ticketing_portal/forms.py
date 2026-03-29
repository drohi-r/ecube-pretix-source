from django import forms
from django.utils.translation import gettext_lazy as _

from .services import (
    PORTAL_CATEGORY_CHOICES,
    PORTAL_LABEL_CHOICES,
    PORTAL_VISIBILITY_CHOICES,
)


class PortalSettingsForm(forms.Form):
    portal_visibility = forms.ChoiceField(
        choices=PORTAL_VISIBILITY_CHOICES,
        label=_("Portal visibility"),
        help_text=_("Auto includes public events, hidden excludes them, and listed can expose private events."),
    )
    portal_label = forms.ChoiceField(
        choices=PORTAL_LABEL_CHOICES,
        required=False,
        label=_("Portal label"),
        help_text=_("Optional badge to render on the portal for restricted or application-gated events."),
    )
    portal_category = forms.ChoiceField(
        choices=PORTAL_CATEGORY_CHOICES,
        required=False,
        label=_("Portal category"),
        help_text=_("Portal-only categorization used for filter pills and query filtering."),
    )
    portal_sort_order = forms.IntegerField(
        required=False,
        min_value=0,
        label=_("Manual sort order"),
        help_text=_("Lower numbers appear first. Leave at 0 to use the default date-based ordering."),
    )
    portal_show_image = forms.BooleanField(
        required=False,
        label=_("Show image on portal"),
        help_text=_("Display the event cover photo on the portal card and hero. Uncheck to hide."),
    )
    portal_custom_image = forms.FileField(
        required=False,
        label=_("Custom portal image"),
        help_text=_("Upload a custom image for this event on the portal. Overrides the theme hero image. Recommended: 1600×900."),
    )

    def clean_portal_sort_order(self):
        return self.cleaned_data.get("portal_sort_order") or 0
