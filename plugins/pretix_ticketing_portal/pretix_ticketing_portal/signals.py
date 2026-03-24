from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_event_settings


@receiver(nav_event_settings, dispatch_uid="pretix_ticketing_portal_nav_event_settings")
def navbar_event_settings(sender, request=None, **kwargs):
    if not request or not getattr(request, "event", None):
        return []

    return [{
        "label": _("Ticketing Portal"),
        "url": reverse(
            "plugins:pretix_ticketing_portal:event_settings",
            kwargs={
                "organizer": request.organizer.slug,
                "event": request.event.slug,
            },
        ),
        "active": "settings/ticketing-portal" in request.path,
    }]
