from django.urls import re_path

from . import views

app_name = "pretix_admissions"

urlpatterns = [
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/$",
        views.control_credentials_list,
        name="control_credentials_list",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/import$",
        views.control_credentials_import,
        name="control_credentials_import",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/import/sample$",
        views.control_credentials_import_sample,
        name="control_credentials_import_sample",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/settings/$",
        views.control_credentials_settings,
        name="control_credentials_settings",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/create$",
        views.control_credential_create,
        name="control_credential_create",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/(?P<pk>\d+)/$",
        views.control_credential_detail,
        name="control_credential_detail",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/(?P<pk>\d+)/print$",
        views.control_credential_print,
        name="control_credential_print",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/(?P<pk>\d+)/revoke$",
        views.control_credential_revoke,
        name="control_credential_revoke",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/(?P<pk>\d+)/block$",
        views.control_credential_block,
        name="control_credential_block",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/credentials/(?P<pk>\d+)/reactivate$",
        views.control_credential_reactivate,
        name="control_credential_reactivate",
    ),

    # legacy compatibility
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/admissions/$",
        views.control_credentials_list,
        name="control_credentials_list_legacy",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/admissions/create$",
        views.control_credential_create,
        name="control_credential_create_legacy",
    ),
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/admissions/(?P<pk>\d+)/$",
        views.control_credential_detail,
        name="control_credential_detail_legacy",
    ),
]
