from django.urls import path, re_path

from .views import PortalAliasRedirectView, PortalDashboardView, PortalIndexView, PortalSettingsView


app_name = "pretix_ticketing_portal"

root_urlpatterns = [
    path("", PortalIndexView.as_view(), name="portal_root"),
]

urlpatterns = [
    path("portal/", PortalAliasRedirectView.as_view(), name="portal_index"),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/settings/ticketing-portal/$",
        PortalSettingsView.as_view(),
        name="event_settings",
    ),
    re_path(
        r"^control/organizer/(?P<organizer>[^/]+)/settings/portal-dashboard/$",
        PortalDashboardView.as_view(),
        name="organizer_dashboard",
    ),
]
