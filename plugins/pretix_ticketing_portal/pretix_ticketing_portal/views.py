from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic.edit import FormView
from pretix.control.permissions import EventPermissionRequiredMixin
from pretix.control.views.event import EventSettingsViewMixin

from .forms import PortalSettingsForm
from .services import build_portal_context


class PortalSettingsView(EventPermissionRequiredMixin, EventSettingsViewMixin, FormView):
    template_name = "pretix_ticketing_portal/control_settings.html"
    form_class = PortalSettingsForm
    permission = "can_change_event_settings"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        initial = {
            "portal_featured": self.request.event.settings.get("portal_featured", as_type=bool, default=False),
            "portal_visibility": self.request.event.settings.get("portal_visibility", default="auto") or "auto",
            "portal_label": self.request.event.settings.get("portal_label", default="") or "",
            "portal_category": self.request.event.settings.get("portal_category", default="") or "",
            "portal_sort_order": self.request.event.settings.get("portal_sort_order", as_type=int, default=0) or 0,
        }
        if self.request.method == "GET":
            kwargs["initial"] = initial
        return kwargs

    def form_valid(self, form):
        self.request.event.settings.set("portal_featured", form.cleaned_data["portal_featured"])
        self.request.event.settings.set("portal_visibility", form.cleaned_data["portal_visibility"])
        self.request.event.settings.set("portal_label", form.cleaned_data["portal_label"])
        self.request.event.settings.set("portal_category", form.cleaned_data["portal_category"])
        self.request.event.settings.set("portal_sort_order", form.cleaned_data["portal_sort_order"])
        self.request.event.cache.clear()

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


class PortalIndexView(View):
    template_name = "pretix_ticketing_portal/portal_index.html"

    def get(self, request, *args, **kwargs):
        context = build_portal_context(category_filter=request.GET.get("category", ""))
        context.update({
            "portal_active_path": request.path,
            "portal_about_url": "https://ecube-entertainment.com/about-platform",
            "portal_source_url": "https://github.com/drohi-r/ecube-pretix",
        })
        return render(request, self.template_name, context)


class PortalAliasRedirectView(View):
    def get(self, request, *args, **kwargs):
        target = "/"
        if request.META.get("QUERY_STRING"):
            target = f"{target}?{request.META['QUERY_STRING']}"
        return HttpResponseRedirect(target)
