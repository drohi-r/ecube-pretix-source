from django.contrib import messages
from django.dispatch import receiver
from django.http import HttpResponseRedirect
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _

from pretix.base.signals import order_placed
from pretix.control.signals import nav_event, nav_event_settings
from pretix.multidomain.urlreverse import build_absolute_uri
from pretix.presale.signals import front_page_top, html_head as presale_html_head, process_request

from .models import ApplicationStatus, ExclusiveAccessApplication


def _protected_item_ids(event):
    return set(event.settings.get("exclusive_access_protected_items", as_type=list) or [])


def _get_theme_primary(event):
    """Get the event's visual theme color from the ecube design system,
    falling back to Pretix's primary_color setting."""
    try:
        from pretix_event_themes.theme_config import PRESET_DEFAULTS
        preset = (
            event.settings.get("ecube_theme_preset", default="")
            or event.settings.get("ecube_theme", default="")
        )
        if preset and preset in PRESET_DEFAULTS:
            return PRESET_DEFAULTS[preset]["primary_color"]
    except Exception:
        pass
    return event.settings.get("primary_color", default="") or "#C8000A"


def _access_cookie_name(event):
    return f"exclusive_access_{event.slug}"


def _has_approved_access_for_request(event, request):
    if request is None:
        return False

    token = request.COOKIES.get(_access_cookie_name(event), "")
    if not token:
        return False

    return ExclusiveAccessApplication.objects.filter(
        event=event,
        access_token=token,
        status=ApplicationStatus.APPROVED,
    ).exists()


def _request_access_url(event):
    return build_absolute_uri(
        event,
        "plugins:pretix_exclusive_access:request_access",
    )


@receiver(nav_event_settings, dispatch_uid="pretix_exclusive_access_nav_settings")
def nav_settings(sender, request, **kwargs):
    if not getattr(request, "event", None):
        return []
    url = resolve(request.path_info)
    return [{
        "label": _("Exclusive Access"),
        "url": reverse(
            "plugins:pretix_exclusive_access:settings",
            kwargs={
                "organizer": request.organizer.slug,
                "event": request.event.slug,
            },
        ),
        "active": (
            url.namespace == "plugins:pretix_exclusive_access"
            and url.url_name == "settings"
        ),
    }]


@receiver(nav_event, dispatch_uid="pretix_exclusive_access_nav_event")
def nav_event_receiver(sender, request, **kwargs):
    if not getattr(request, "event", None):
        return []
    if not request.user.has_event_permission(request.organizer, request.event, "can_change_event_settings"):
        return []
    url = resolve(request.path_info)
    return [{
        "label": _("Exclusive Access Applications"),
        "icon": "lock",
        "url": reverse(
            "plugins:pretix_exclusive_access:applications",
            kwargs={
                "organizer": request.organizer.slug,
                "event": request.event.slug,
            },
        ),
        "active": (
            url.namespace == "plugins:pretix_exclusive_access"
            and url.url_name in {"applications", "application_detail"}
        ),
    }]


@receiver(presale_html_head, dispatch_uid="pretix_exclusive_access_presale_head")
def presale_head(sender, request=None, **kwargs):
    protected = _protected_item_ids(sender)
    if not protected:
        return ""
    brand = _get_theme_primary(sender)
    return f"""
<style>
.exclusive-access-cta {{
    margin: 18px 0 24px 0;
    padding: 18px 20px;
    border: 1px solid rgba(200,0,10,.18);
    border-radius: 12px;
    background: rgba(200,0,10,.05);
}}
.exclusive-access-cta h3 {{
    margin: 0 0 8px 0;
}}
.exclusive-access-cta p {{
    margin: 0 0 10px 0;
}}
.exclusive-access-cta.approved {{
    border-color: rgba(31,143,85,.22);
    background: rgba(31,143,85,.06);
}}

.exclusive-access-cta .exclusive-access-btn,
.exclusive-access-cta a.exclusive-access-btn.btn,
.exclusive-access-cta a.exclusive-access-btn.btn.btn-primary {{
    display: inline-block;
    background: {brand} !important;
    border: 1px solid {brand} !important;
    color: #fff !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: .08em !important;
    text-decoration: none !important;
}}

.exclusive-access-cta .exclusive-access-btn:hover,
.exclusive-access-cta a.exclusive-access-btn.btn:hover,
.exclusive-access-cta a.exclusive-access-btn.btn.btn-primary:hover {{
    filter: brightness(.85);
    text-decoration: none !important;
}}

.exclusive-access-cta .exclusive-access-btn-label {{
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
    background: none !important;
}}

</style>
"""

@receiver(front_page_top, dispatch_uid="pretix_exclusive_access_frontpage_top")
def frontpage_top(sender, request=None, **kwargs):
    protected = _protected_item_ids(sender)
    if not protected:
        return ""

    approved = _has_approved_access_for_request(sender, request)
    access_url = _request_access_url(sender)

    if approved:
        return """
<div class="exclusive-access-cta approved">
    <h3>Access Approved</h3>
    <p>Your browser is approved for protected access products on this event.</p>
</div>
"""

    return f"""
<div class="exclusive-access-cta">
    <h3>Private Access</h3>
    <p>This event contains protected access products. If you have not yet been approved, request access below.</p>
    <a class="btn btn-primary exclusive-access-btn" href="{access_url}"><span class="exclusive-access-btn-label">Request Access</span></a>
</div>
"""

@receiver(process_request, dispatch_uid="pretix_exclusive_access_process_request")
def process_request_receiver(sender, request=None, **kwargs):
    protected = _protected_item_ids(sender)
    if not protected or request is None:
        return None

    if "cart/add" not in request.path:
        return None

    if _has_approved_access_for_request(sender, request):
        return None

    posted_values = list(request.POST.keys()) + list(request.POST.values())
    posted_text = " ".join(str(v) for v in posted_values)

    for item_id in protected:
        if str(item_id) in posted_text:
            messages.error(
                request,
                _("This product requires approved access. Please use your private access link or request access first.")
            )
            return HttpResponseRedirect(_request_access_url(sender))

    return None


@receiver(order_placed, dispatch_uid="pretix_exclusive_access_order_link")
def order_link_receiver(sender, order=None, **kwargs):
    if not order:
        return

    event = order.event
    positions = list(order.positions.select_related("item"))

    for pos in positions:
        email_candidates = []

        if getattr(order, "email", None):
            email_candidates.append(order.email.strip().lower())
        if getattr(pos, "attendee_email", None):
            email_candidates.append(pos.attendee_email.strip().lower())

        email_candidates = [e for e in email_candidates if e]
        if not email_candidates:
            continue

        app = (
            ExclusiveAccessApplication.objects
            .filter(
                event=event,
                item=pos.item,
                status=ApplicationStatus.APPROVED,
                email__in=email_candidates,
                approved_order_position__isnull=True,
            )
            .order_by("-reviewed_at", "-created_at")
            .first()
        )

        if app:
            app.approved_order_code = order.code
            app.approved_order_position = pos
            app.save(update_fields=["approved_order_code", "approved_order_position", "updated_at"])


@receiver(presale_html_head, dispatch_uid="pretix_exclusive_access_presale_static_css")
def presale_head_static_css(sender, request=None, **kwargs):
    protected = _protected_item_ids(sender)
    if not protected:
        return ""
    return '<link rel="stylesheet" type="text/css" href="/static/pretix_exclusive_access/public-cta-v2.css?v=20260325a">'
