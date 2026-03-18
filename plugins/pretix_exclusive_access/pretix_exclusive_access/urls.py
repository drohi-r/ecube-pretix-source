from django.urls import re_path
from pretix.multidomain import event_url

from .views import (
    ApplicationDetailView,
    ApplicationListView,
    ApprovedAccessView,
    ExclusiveAccessSettingsView,
    RequestAccessSuccessView,
    RequestAccessView,
)

event_patterns = [
    event_url(r"^request-access/$", RequestAccessView.as_view(), name="request_access"),
    event_url(r"^request-access/success/$", RequestAccessSuccessView.as_view(), name="request_success"),
    event_url(r"^access/(?P<token>[A-Za-z0-9]+)/$", ApprovedAccessView.as_view(), name="approved_access"),
]

urlpatterns = [
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/settings/exclusive-access/$",
        ExclusiveAccessSettingsView.as_view(),
        name="settings",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/exclusive-access/$",
        ApplicationListView.as_view(),
        name="applications",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/exclusive-access/(?P<application_id>\d+)/$",
        ApplicationDetailView.as_view(),
        name="application_detail",
    ),
]

