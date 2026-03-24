from django import forms
from django.utils.translation import gettext_lazy as _

from .services import (
    PORTAL_CATEGORY_CHOICES,
    PORTAL_LABEL_CHOICES,
    PORTAL_VISIBILITY_CHOICES,
)


class PortalSettingsForm(forms.Form):
    portal_featured = forms.BooleanField(
        required=False,
        label=_("Featured"),
        help_text=_("Mark this event as featured and eligible for the portal hero spotlight."),
    )
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

    def clean_portal_sort_order(self):
        return self.cleaned_data.get("portal_sort_order") or 0
