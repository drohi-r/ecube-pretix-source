from django.urls import re_path
from .views import EventThemesSettingsView, OrganizerThemesSettingsView

urlpatterns = [
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/settings/themes/$",
        EventThemesSettingsView.as_view(),
        name="event_settings",
    ),
    re_path(
        r"^control/organizer/(?P<organizer>[^/]+)/settings/themes/$",
        OrganizerThemesSettingsView.as_view(),
        name="organizer_settings",
    ),
]

