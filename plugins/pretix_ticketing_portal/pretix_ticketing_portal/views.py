import logging

from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic.edit import FormView
from django_scopes import scopes_disabled
from pretix.base.models import Event
from pretix.control.permissions import EventPermissionRequiredMixin, OrganizerPermissionRequiredMixin
from pretix.control.views.event import EventSettingsViewMixin

from .forms import PortalSettingsForm
from .services import (
    PORTAL_CATEGORY_CHOICES,
    PORTAL_LABEL_CHOICES,
    PORTAL_VISIBILITY_CHOICES,
    build_portal_context,
    _event_image_url,
)

logger = logging.getLogger(__name__)

PORTAL_IMAGE_SUBDIR = "pub/portal_images"


def _portal_image_upload_path(event, filename):
    safe_name = filename.replace(" ", "_").replace("/", "_")
    return f"{PORTAL_IMAGE_SUBDIR}/{event.organizer.slug}/{event.slug}/{safe_name}"


def _save_custom_image(event, uploaded_file):
    old_path = event.settings.get("portal_custom_image_path", default="")
    if old_path:
        try:
            default_storage.delete(old_path)
        except Exception:
            logger.warning("Failed to delete old portal image: %s", old_path, exc_info=True)

    path = _portal_image_upload_path(event, uploaded_file.name)
    saved_path = default_storage.save(path, uploaded_file)
    url = default_storage.url(saved_path)
    event.settings.set("portal_custom_image_path", saved_path)
    event.settings.set("portal_custom_image_url", url)


def _remove_custom_image(event):
    old_path = event.settings.get("portal_custom_image_path", default="")
    if old_path:
        try:
            default_storage.delete(old_path)
        except Exception:
            logger.warning("Failed to delete portal image: %s", old_path, exc_info=True)
    event.settings.set("portal_custom_image_path", "")
    event.settings.set("portal_custom_image_url", "")


# ── Per-event settings ──────────────────────────────────────

class PortalSettingsView(EventPermissionRequiredMixin, EventSettingsViewMixin, FormView):
    template_name = "pretix_ticketing_portal/control_settings.html"
    form_class = PortalSettingsForm
    permission = "can_change_event_settings"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        initial = {
            "portal_visibility": self.request.event.settings.get("portal_visibility", default="auto") or "auto",
            "portal_label": self.request.event.settings.get("portal_label", default="") or "",
            "portal_category": self.request.event.settings.get("portal_category", default="") or "",
            "portal_sort_order": self.request.event.settings.get("portal_sort_order", as_type=int, default=0) or 0,
            "portal_show_image": self.request.event.settings.get("portal_show_image", as_type=bool, default=True),
        }
        if initial["portal_show_image"] is None:
            initial["portal_show_image"] = True
        if self.request.method == "GET":
            kwargs["initial"] = initial
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if request.POST.get("remove_portal_image") == "1":
            _remove_custom_image(request.event)
            request.event.cache.clear()
            messages.success(request, "Custom portal image removed.")
            return HttpResponseRedirect(self.get_success_url())
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        event = self.request.event
        event.settings.set("portal_visibility", form.cleaned_data["portal_visibility"])
        event.settings.set("portal_label", form.cleaned_data["portal_label"])
        event.settings.set("portal_category", form.cleaned_data["portal_category"])
        event.settings.set("portal_sort_order", form.cleaned_data["portal_sort_order"])
        event.settings.set("portal_show_image", form.cleaned_data["portal_show_image"])

        uploaded = form.cleaned_data.get("portal_custom_image")
        if uploaded:
            _save_custom_image(event, uploaded)

        event.cache.clear()
        messages.success(self.request, "Ticketing portal settings saved.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "plugins:pretix_ticketing_portal:event_settings",
            kwargs={
                "organizer": self.request.organizer.slug,
                "event": self.request.event.slug,
            },
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_custom_image_url"] = self.request.event.settings.get("portal_custom_image_url", default="")
        return ctx


# ── Organizer-level portal dashboard ────────────────────────

class PortalDashboardView(OrganizerPermissionRequiredMixin, View):
    permission = "can_change_organizer_settings"
    template_name = "pretix_ticketing_portal/portal_dashboard.html"

    def get(self, request, organizer, *args, **kwargs):
        event_rows, hero_event_id = self._build_rows(request.organizer)
        resp = render(request, self.template_name, self._context(event_rows, hero_event_id))
        resp['Content-Security-Policy'] = "style-src 'unsafe-inline' 'self'"
        return resp

    def post(self, request, organizer, *args, **kwargs):
        hero_pk = request.POST.get("hero_event", "")

        with scopes_disabled():
            events = list(Event.objects.filter(organizer=request.organizer).order_by("date_from"))

        for event in events:
            slug = event.slug
            is_hero = str(event.pk) == hero_pk

            event.settings.set("portal_featured", is_hero)
            event.settings.set("portal_hero_priority", 1 if is_hero else 0)
            event.settings.set("portal_sort_order", self._int_field(request, f"portal_sort_order__{slug}"))
            event.settings.set("portal_visibility", request.POST.get(f"portal_visibility__{slug}", "auto"))
            event.settings.set("portal_show_image", f"portal_show_image__{slug}" in request.POST)
            event.settings.set("portal_category", request.POST.get(f"portal_category__{slug}", ""))
            event.settings.set("portal_label", request.POST.get(f"portal_label__{slug}", ""))

            uploaded = request.FILES.get(f"portal_custom_image__{slug}")
            if uploaded:
                _save_custom_image(event, uploaded)

            if request.POST.get(f"remove_image__{slug}") == "1":
                _remove_custom_image(event)

            event.cache.clear()

        messages.success(request, "Portal dashboard saved.")
        return HttpResponseRedirect(
            reverse("plugins:pretix_ticketing_portal:organizer_dashboard",
                    kwargs={"organizer": request.organizer.slug})
        )

    def _build_rows(self, org):
        with scopes_disabled():
            events = list(Event.objects.filter(organizer=org).order_by("date_from"))

        hero_event_id = None
        rows = []
        for event in events:
            featured = event.settings.get("portal_featured", as_type=bool, default=False)
            hero_priority = int(event.settings.get("portal_hero_priority", as_type=int, default=0) or 0)
            show_image = event.settings.get("portal_show_image", as_type=bool, default=True)
            if show_image is None:
                show_image = True
            custom_url = event.settings.get("portal_custom_image_url", default="")
            theme_url = _event_image_url(event) if show_image else ""
            display_url = custom_url or theme_url

            if featured and (hero_event_id is None or hero_priority > 0):
                hero_event_id = event.pk

            rows.append({
                "event": event,
                "sort_order": int(event.settings.get("portal_sort_order", as_type=int, default=0) or 0),
                "visibility": event.settings.get("portal_visibility", default="auto") or "auto",
                "show_image": show_image,
                "category": event.settings.get("portal_category", default="") or "",
                "label": event.settings.get("portal_label", default="") or "",
                "custom_image_url": custom_url,
                "image_url": display_url,
            })
        return rows, hero_event_id

    def _context(self, event_rows, hero_event_id):
        return {
            "event_rows": event_rows,
            "hero_event_id": hero_event_id,
            "visibility_choices": PORTAL_VISIBILITY_CHOICES,
            "category_choices": PORTAL_CATEGORY_CHOICES,
            "label_choices": PORTAL_LABEL_CHOICES,
        }

    @staticmethod
    def _int_field(request, name):
        try:
            return max(0, int(request.POST.get(name, 0)))
        except (TypeError, ValueError):
            return 0


# ── Public portal views ─────────────────────────────────────

class PortalIndexView(View):
    template_name = "pretix_ticketing_portal/portal_index.html"

    def get(self, request, *args, **kwargs):
        context = build_portal_context(category_filter=request.GET.get("category", ""))

        # Resolve account login URL from the first organizer
        portal_account_url = "#"
        with scopes_disabled():
            from pretix.base.models import Organizer
            org = Organizer.objects.first()
            if org:
                portal_account_url = f"/{org.slug}/account/login"

        context.update({
            "portal_active_path": request.path,
            "portal_about_url": "https://ecube-entertainment.com/about-platform",
            "portal_source_url": "https://github.com/drohi-r/ecube-pretix",
            "portal_account_url": portal_account_url,
        })
        return render(request, self.template_name, context)


class PortalAliasRedirectView(View):
    def get(self, request, *args, **kwargs):
        target = "/"
        if request.META.get("QUERY_STRING"):
            target = f"{target}?{request.META['QUERY_STRING']}"
        return HttpResponseRedirect(target)
