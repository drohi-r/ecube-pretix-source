from django.urls import path
from . import views

app_name = "pretix_ecube_access"

urlpatterns = [
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/",
        views.control_dashboard,
        name="control_dashboard",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/ops/",
        views.control_ops_dashboard,
        name="control_ops_dashboard",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/doors/",
        views.control_doors_list,
        name="control_doors_list",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/doors/create/",
        views.control_door_create,
        name="control_door_create",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/doors/<int:pk>/edit/",
        views.control_door_edit,
        name="control_door_edit",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/doors/<int:pk>/regenerate-token/",
        views.control_door_regenerate_token,
        name="control_door_regenerate_token",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/doors/<int:pk>/delete/",
        views.control_door_delete,
        name="control_door_delete",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/scan/",
        views.control_scan_shell,
        name="control_scan_shell",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/door/",
        views.control_door_shell,
        name="control_door_shell",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/logs/",
        views.control_scan_logs,
        name="control_scan_logs",
    ),
    path(
        "control/event/<str:organizer>/<str:event>/ecube-access/api/scan/",
        views.api_scan,
        name="api_scan",
    ),
]

event_patterns = [
    path(
        "access/<str:door_slug>/<str:door_token>/",
        views.public_door_shell,
        name="public_door_shell",
    ),
    path(
        "access/<str:door_slug>/<str:door_token>/scan/",
        views.public_api_scan,
        name="public_api_scan",
    ),
    path(
        "access/<str:door_slug>/<str:door_token>/lock/",
        views.public_door_lock,
        name="public_door_lock",
    ),
]

