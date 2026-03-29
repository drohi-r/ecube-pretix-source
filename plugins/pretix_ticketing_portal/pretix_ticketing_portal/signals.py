from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_event_settings, nav_global


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


@receiver(nav_global, dispatch_uid="pretix_ticketing_portal_nav_global_dashboard")
def navbar_global_dashboard(sender, request=None, **kwargs):
    if not request:
        return []
    if not getattr(request.user, "is_staff", False) and not getattr(request.user, "is_superuser", False):
        return []

    from pretix.base.models import Organizer
    from django_scopes import scopes_disabled
    with scopes_disabled():
        org = Organizer.objects.first()
    if not org:
        return []

    return [{
        "label": _("Portal Dashboard"),
        "icon": "globe",
        "url": reverse(
            "plugins:pretix_ticketing_portal:organizer_dashboard",
            kwargs={"organizer": org.slug},
        ),
        "active": "settings/portal-dashboard" in request.path,
    }]
