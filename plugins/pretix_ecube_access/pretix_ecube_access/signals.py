from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_event


@receiver(nav_event, dispatch_uid="pretix_ecube_access_nav")
def control_nav(sender, request=None, **kwargs):
    if not request or not getattr(request, "event", None):
        return []

    url = reverse(
        "plugins:pretix_ecube_access:control_dashboard",
        kwargs={
            "organizer": request.event.organizer.slug,
            "event": request.event.slug,
        },
    )

    namespaces = []
    if getattr(request, "resolver_match", None):
        namespaces = list(getattr(request.resolver_match, "namespaces", []) or [])

    return [
        {
            "label": _("Ecube Access"),
            "url": url,
            "icon": "ticket",
            "active": "pretix_ecube_access" in namespaces,
        }
    ]

