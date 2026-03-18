from datetime import timedelta

from django import forms
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.edit import FormView

from pretix.control.permissions import EventPermissionRequiredMixin
from pretix.control.views.event import EventSettingsViewMixin
from pretix.presale.views import EventViewMixin

from .admin_services import (
    approve_application_v11,
    reject_application_v11,
    bulk_approve_applications_v11,
    bulk_reject_applications_v11,
    export_applications_csv_v11,
)
from .forms import (
    ExclusiveAccessApplicationForm,
    PUBLIC_FORM_FIELD_SPECS,
    get_exclusive_access_form_config,
)
from .models import ExclusiveAccessApplication, ApplicationStatus
from .services import approve_application as legacy_approve_application
from .services import reject_application as legacy_reject_application


class ExclusiveAccessSettingsForm(forms.Form):
    protected_items = forms.MultipleChoiceField(
        required=False,
        label=_("Protected items"),
        widget=forms.CheckboxSelectMultiple
    )
    voucher_validity_days = forms.IntegerField(
        required=True,
        min_value=1,
        initial=7,
        label=_("Voucher validity (days)")
    )
    approval_email_subject = forms.CharField(
        required=True,
        max_length=255,
        initial=_("Your access request has been approved"),
        label=_("Approval email subject")
    )
    rejection_email_subject = forms.CharField(
        required=True,
        max_length=255,
        initial=_("Update on your access request"),
        label=_("Rejection email subject")
    )

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        items = list(event.items.filter(active=True).order_by("name")) if event else []
        self.fields["protected_items"].choices = [(str(i.pk), str(i.name)) for i in items]

        config = get_exclusive_access_form_config(event)
        for spec in PUBLIC_FORM_FIELD_SPECS:
            name = spec["name"]
            label = spec["label"]
            self.fields[f"show_{name}"] = forms.BooleanField(
                required=False,
                label=_("Show: %(field)s") % {"field": label},
                initial=config[name]["show"],
            )
            self.fields[f"require_{name}"] = forms.BooleanField(
                required=False,
                label=_("Require: %(field)s") % {"field": label},
                initial=config[name]["required"],
            )


class ExclusiveAccessSettingsView(EventSettingsViewMixin, FormView):
    template_name = "pretix_exclusive_access/control_settings.html"
    form_class = ExclusiveAccessSettingsForm
    permission = "can_change_event_settings"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["event"] = self.request.event

        protected_ids = self.request.event.settings.get(
            "exclusive_access_protected_items",
            as_type=list,
        ) or []

        initial = {
            "protected_items": [str(i) for i in protected_ids],
            "voucher_validity_days": self.request.event.settings.get(
                "exclusive_access_voucher_validity_days",
                as_type=int,
                default=7,
            ) or 7,
            "approval_email_subject": self.request.event.settings.get(
                "exclusive_access_approval_email_subject",
                default="Your access request has been approved",
            ) or "Your access request has been approved",
            "rejection_email_subject": self.request.event.settings.get(
                "exclusive_access_rejection_email_subject",
                default="Update on your access request",
            ) or "Update on your access request",
        }

        config = get_exclusive_access_form_config(self.request.event)
        for spec in PUBLIC_FORM_FIELD_SPECS:
            name = spec["name"]
            initial[f"show_{name}"] = config[name]["show"]
            initial[f"require_{name}"] = config[name]["required"]

        if self.request.method == "GET":
            kwargs["initial"] = initial
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx.get("form")
        rows = []
        if form is not None:
            for spec in PUBLIC_FORM_FIELD_SPECS:
                name = spec["name"]
                rows.append(
                    {
                        "name": name,
                        "label": spec["label"],
                        "show_field": form[f"show_{name}"],
                        "require_field": form[f"require_{name}"],
                    }
                )
        ctx["field_rows"] = rows
        return ctx

    def form_valid(self, form):
        self.request.event.settings.set(
            "exclusive_access_protected_items",
            [int(x) for x in form.cleaned_data["protected_items"]],
        )
        self.request.event.settings.set(
            "exclusive_access_voucher_validity_days",
            form.cleaned_data["voucher_validity_days"],
        )
        self.request.event.settings.set(
            "exclusive_access_approval_email_subject",
            form.cleaned_data["approval_email_subject"],
        )
        self.request.event.settings.set(
            "exclusive_access_rejection_email_subject",
            form.cleaned_data["rejection_email_subject"],
        )

        for spec in PUBLIC_FORM_FIELD_SPECS:
            name = spec["name"]
            show = bool(form.cleaned_data.get(f"show_{name}"))
            require = bool(form.cleaned_data.get(f"require_{name}")) if show else False
            self.request.event.settings.set(f"exclusive_access_show_{name}", show)
            self.request.event.settings.set(f"exclusive_access_require_{name}", require)

        messages.success(self.request, _("Exclusive Access settings saved."))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "plugins:pretix_exclusive_access:settings",
            kwargs={
                "organizer": self.request.organizer.slug,
                "event": self.request.event.slug,
            },
        )


class RequestAccessView(EventViewMixin, View):
    template_name = "pretix_exclusive_access/event_request_access.html"

    def get_protected_items(self):
        ids = self.request.event.settings.get(
            "exclusive_access_protected_items",
            as_type=list,
        ) or []
        return self.request.event.items.filter(id__in=ids, active=True).order_by("name")

    def dispatch(self, request, *args, **kwargs):
        if not self.get_protected_items().exists():
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = ExclusiveAccessApplicationForm(
            protected_items=self.get_protected_items(),
            event=request.event,
        )
        return render(request, self.template_name, {"event": request.event, "form": form})

    def post(self, request, *args, **kwargs):
        form = ExclusiveAccessApplicationForm(
            request.POST,
            request.FILES,
            protected_items=self.get_protected_items(),
            event=request.event,
        )
        if form.is_valid():
            app = form.save(commit=False)
            app.event = request.event
            app.email = (app.email or "").strip().lower()

            selected_item = form.cleaned_data.get("item") or form.cleaned_data.get("requested_item")
            if not selected_item:
                messages.error(request, _("Please select a ticket type."))
                return render(request, self.template_name, {"event": request.event, "form": form})

            app.item = selected_item

            existing = ExclusiveAccessApplication.objects.filter(
                event=request.event,
                email__iexact=app.email,
            ).exists()

            if existing:
                messages.error(request, _("An application already exists for this email and ticket type."))
                return render(request, self.template_name, {"event": request.event, "form": form})

            try:
                app.save()
            except IntegrityError as e:
                print("EXCLUSIVE ACCESS SAVE INTEGRITY ERROR:", repr(e))
                messages.error(request, _("Application submission failed. Please try again or contact support."))
            else:
                return HttpResponseRedirect(
                    reverse(
                        "plugins:pretix_exclusive_access:request_success",
                        kwargs={
                            "organizer": request.organizer.slug,
                            "event": request.event.slug
                        },
                    )
                )
        return render(request, self.template_name, {"event": request.event, "form": form})


class RequestAccessSuccessView(EventViewMixin, View):
    template_name = "pretix_exclusive_access/event_request_access_success.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"event": request.event})


class ApprovedAccessView(EventViewMixin, View):
    template_name = "pretix_exclusive_access/event_access_approved.html"

    def get(self, request, token, *args, **kwargs):
        application = get_object_or_404(
            ExclusiveAccessApplication,
            event=request.event,
            access_token=token,
            status=ApplicationStatus.APPROVED,
        )

        response = render(
            request,
            self.template_name,
            {
                "event": request.event,
                "application": application,
            },
        )
        response.set_cookie(
            f"exclusive_access_{request.event.slug}",
            token,
            max_age=60 * 60 * 24 * 30,
            httponly=False,
            samesite="Lax",
        )
        return response


class ApplicationListView(EventPermissionRequiredMixin, View):
    permission = "can_change_event_settings"
    template_name = "pretix_exclusive_access/control_applications_list.html"

    def get_queryset(self, request):
        item_field = "requested_item" if hasattr(ExclusiveAccessApplication, "requested_item") else "item"

        qs = ExclusiveAccessApplication.objects.filter(event=request.event).select_related(
            item_field, "reviewed_by"
        )

        status = request.GET.get("status", "").strip()
        guest_category = request.GET.get("guest_category", "").strip()
        gender = request.GET.get("gender", "").strip()
        q = request.GET.get("q", "").strip()

        if status:
            qs = qs.filter(status=status)

        if guest_category and hasattr(ExclusiveAccessApplication, "guest_category"):
            qs = qs.filter(guest_category=guest_category)

        if gender and hasattr(ExclusiveAccessApplication, "gender"):
            if gender == "unspecified":
                qs = qs.filter(Q(gender="") | Q(gender__isnull=True))
            else:
                qs = qs.filter(gender=gender)

        if q:
            q_filter = (
                Q(email__icontains=q) |
                Q(phone__icontains=q) |
                Q(referred_by__icontains=q)
            )

            if hasattr(ExclusiveAccessApplication, "name"):
                q_filter |= Q(name__icontains=q)
            if hasattr(ExclusiveAccessApplication, "full_name"):
                q_filter |= Q(full_name__icontains=q)
            if hasattr(ExclusiveAccessApplication, "instagram"):
                q_filter |= Q(instagram__icontains=q)
            if hasattr(ExclusiveAccessApplication, "instagram_handle"):
                q_filter |= Q(instagram_handle__icontains=q)
            if hasattr(ExclusiveAccessApplication, "approved_order_code"):
                q_filter |= Q(approved_order_code__icontains=q)
            if hasattr(ExclusiveAccessApplication, "gender"):
                q_filter |= Q(gender__icontains=q)

            qs = qs.filter(q_filter)

        if hasattr(ExclusiveAccessApplication, "submitted_at"):
            return qs.order_by("-submitted_at")
        if hasattr(ExclusiveAccessApplication, "created_at"):
            return qs.order_by("-created_at")
        return qs.order_by("-pk")

    def build_dashboard(self, request, qs):
        base_qs = ExclusiveAccessApplication.objects.filter(event=request.event)
        date_field = "submitted_at" if hasattr(ExclusiveAccessApplication, "submitted_at") else "created_at"
        recent_since = timezone.now() - timedelta(days=7)

        shown_count = qs.count()
        total_all = base_qs.count()
        pending_count = qs.filter(status=ApplicationStatus.PENDING).count()
        approved_count = qs.filter(status=ApplicationStatus.APPROVED).count()
        rejected_count = qs.filter(status=ApplicationStatus.REJECTED).count()
        approval_rate = (approved_count / shown_count * 100.0) if shown_count else 0.0
        recent_count = qs.filter(**{f"{date_field}__gte": recent_since}).count()
        missing_photo_count = qs.filter(Q(photo="") | Q(photo__isnull=True)).count()
        linked_order_count = qs.filter(approved_order_position__isnull=False).count()

        item_rows = [
            {"label": row["item__name"] or "-", "count": row["total"]}
            for row in qs.values("item__name").annotate(total=Count("id")).order_by("-total", "item__name")[:8]
        ]

        gender_rows = []
        try:
            gender_choices = dict(ExclusiveAccessApplication._meta.get_field("gender").choices)
            for key, label in gender_choices.items():
                gender_rows.append({"label": label, "count": qs.filter(gender=key).count()})
            gender_rows.append({"label": _("Unspecified"), "count": qs.filter(Q(gender="") | Q(gender__isnull=True)).count()})
        except Exception:
            gender_rows = []

        guest_rows = []
        try:
            guest_choices = dict(ExclusiveAccessApplication._meta.get_field("guest_category").choices)
            for row in qs.values("guest_category").annotate(total=Count("id")).order_by("-total", "guest_category")[:8]:
                key = row["guest_category"] or ""
                guest_rows.append({"label": guest_choices.get(key) or key or _("Unassigned"), "count": row["total"]})
        except Exception:
            guest_rows = []

        source_rows = []
        try:
            source_choices = dict(ExclusiveAccessApplication._meta.get_field("source").choices)
            for row in qs.values("source").annotate(total=Count("id")).order_by("-total", "source")[:8]:
                key = row["source"] or ""
                source_rows.append({"label": source_choices.get(key) or key or "-", "count": row["total"]})
        except Exception:
            source_rows = []

        recent_apps = list(qs[:5])

        return {
            "shown_count": shown_count,
            "total_all": total_all,
            "filters_active": bool(
                request.GET.get("status", "").strip()
                or request.GET.get("guest_category", "").strip()
                or request.GET.get("gender", "").strip()
                or request.GET.get("q", "").strip()
            ),
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "approval_rate": approval_rate,
            "recent_count": recent_count,
            "missing_photo_count": missing_photo_count,
            "linked_order_count": linked_order_count,
            "gender_rows": gender_rows,
            "guest_rows": guest_rows,
            "source_rows": source_rows,
            "item_rows": item_rows,
            "recent_apps": recent_apps,
        }

    def get(self, request, organizer, event, *args, **kwargs):
        qs = self.get_queryset(request)

        if request.GET.get("export") == "csv":
            csv_data = export_applications_csv_v11(qs)
            response = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="exclusive-access-{request.event.slug}.csv"'
            return response

        form_config = get_exclusive_access_form_config(request.event)
        field_rows = []
        for spec in PUBLIC_FORM_FIELD_SPECS:
            meta = form_config.get(spec["name"], {})
            field_rows.append(
                {
                    "name": spec["name"],
                    "label": spec["label"],
                    "show": bool(meta.get("show")),
                    "required": bool(meta.get("required")),
                }
            )

        return render(
            request,
            self.template_name,
            {
                "event": request.event,
                "applications": qs,
                "status": request.GET.get("status", "").strip(),
                "guest_category": request.GET.get("guest_category", "").strip(),
                "gender": request.GET.get("gender", "").strip(),
                "q": request.GET.get("q", "").strip(),
                "dashboard": self.build_dashboard(request, qs),
                "field_rows": field_rows,
            },
        )

    def post(self, request, organizer, event, *args, **kwargs):
        action = request.POST.get("action")
        guest_category = request.POST.get("guest_category", "").strip() or None
        status_reason = request.POST.get("status_reason", "").strip() or None
        internal_note = request.POST.get("internal_note", "").strip() or None

        selected_ids = request.POST.getlist("selected_applications")
        use_filtered = request.POST.get("select_all_filtered") == "1"

        if use_filtered and action in ["bulk_approve", "bulk_reject", "export_selected"]:
            queryset = self.get_queryset(request)
            selected_ids = list(queryset.values_list("pk", flat=True))
        else:
            if not selected_ids:
                single_id = request.POST.get("application_id")
                if single_id:
                    selected_ids = [single_id]
            queryset = ExclusiveAccessApplication.objects.filter(
                event=request.event,
                pk__in=selected_ids,
            )

        if action == "export_selected":
            if not selected_ids:
                messages.error(request, _("No applications selected."))
            else:
                csv_data = export_applications_csv_v11(queryset)
                response = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
                response["Content-Disposition"] = f'attachment; filename="exclusive-access-selected-{request.event.slug}.csv"'
                return response

        elif action == "bulk_approve":
            if not selected_ids:
                messages.error(request, _("No applications selected."))
            else:
                approved_count = 0
                skipped_count = 0

                for application in queryset:
                    if getattr(application, "status", None) == "approved":
                        skipped_count += 1
                        continue
                    try:
                        legacy_approve_application(application, request.user)
                        approve_application_v11(
                            application,
                            reviewed_by=request.user,
                            guest_category=guest_category,
                            status_reason=status_reason,
                            internal_note=internal_note,
                            send_email=False,
                        )
                        approved_count += 1
                    except Exception:
                        skipped_count += 1

                messages.success(
                    request,
                    _("Bulk approve complete. Approved: %(approved)s, skipped: %(skipped)s")
                    % {"approved": approved_count, "skipped": skipped_count},
                )

        elif action == "bulk_reject":
            if not selected_ids:
                messages.error(request, _("No applications selected."))
            else:
                rejected_count = 0
                skipped_count = 0

                for application in queryset:
                    if getattr(application, "status", None) == "rejected":
                        skipped_count += 1
                        continue
                    try:
                        legacy_reject_application(application, request.user)
                        reject_application_v11(
                            application,
                            reviewed_by=request.user,
                            status_reason=status_reason,
                            internal_note=internal_note,
                        )
                        rejected_count += 1
                    except Exception:
                        skipped_count += 1

                messages.success(
                    request,
                    _("Bulk reject complete. Rejected: %(rejected)s, skipped: %(skipped)s")
                    % {"rejected": rejected_count, "skipped": skipped_count},
                )

        elif action == "approve":
            application = get_object_or_404(
                ExclusiveAccessApplication,
                event=request.event,
                pk=request.POST.get("application_id"),
            )
            try:
                legacy_approve_application(application, request.user)
                approve_application_v11(
                    application,
                    reviewed_by=request.user,
                    guest_category=guest_category,
                    status_reason=status_reason,
                    internal_note=internal_note,
                    send_email=False,
                )
                messages.success(request, _("Application approved and email sent."))
            except Exception as e:
                messages.error(request, _("Approval email failed: %(error)s") % {"error": str(e)})

        elif action == "reject":
            application = get_object_or_404(
                ExclusiveAccessApplication,
                event=request.event,
                pk=request.POST.get("application_id"),
            )
            try:
                legacy_reject_application(application, request.user)
                reject_application_v11(
                    application,
                    reviewed_by=request.user,
                    status_reason=status_reason,
                    internal_note=internal_note,
                )
                messages.success(request, _("Application rejected and email sent."))
            except Exception as e:
                messages.error(request, _("Rejection email failed: %(error)s") % {"error": str(e)})

        else:
            messages.error(request, _("Unknown action."))

        redirect_url = reverse(
            "plugins:pretix_exclusive_access:applications",
            kwargs={
                "organizer": request.organizer.slug,
                "event": request.event.slug,
            },
        )

        q = request.GET.urlencode()
        if q:
            redirect_url = f"{redirect_url}?{q}"

        return HttpResponseRedirect(redirect_url)


class ApplicationDetailView(EventPermissionRequiredMixin, View):
    permission = "can_change_event_settings"
    template_name = "pretix_exclusive_access/control_application_detail.html"

    def get_object(self, request, application_id):
        return get_object_or_404(
            ExclusiveAccessApplication,
            event=request.event,
            pk=application_id,
        )

    def get(self, request, organizer, event, application_id, *args, **kwargs):
        application = self.get_object(request, application_id)
        return render(request, self.template_name, {"event": request.event, "application": application})

    def post(self, request, organizer, event, application_id, *args, **kwargs):
        application = self.get_object(request, application_id)
        action = request.POST.get("action")
        guest_category = request.POST.get("guest_category", "").strip() or None
        status_reason = request.POST.get("status_reason", "").strip() or None
        internal_note = request.POST.get("internal_note", "").strip() or None
        gender = request.POST.get("gender", "").strip() or ""

        if hasattr(application, "gender"):
            application.gender = gender

        if action == "approve":
            try:
                legacy_approve_application(application, request.user)
                approve_application_v11(
                    application,
                    reviewed_by=request.user,
                    guest_category=guest_category,
                    status_reason=status_reason,
                    internal_note=internal_note,
                    send_email=False,
                )
                messages.success(request, _("Application approved and access link sent."))
            except Exception as e:
                messages.error(request, _("Approval email failed: %(error)s") % {"error": str(e)})

        elif action == "reject":
            try:
                legacy_reject_application(application, request.user)
                reject_application_v11(
                    application,
                    reviewed_by=request.user,
                    status_reason=status_reason,
                    internal_note=internal_note,
                )
                messages.success(request, _("Application rejected and email sent."))
            except Exception as e:
                messages.error(request, _("Rejection email failed: %(error)s") % {"error": str(e)})

        elif action == "save":
            changed = False

            if hasattr(application, "guest_category"):
                application.guest_category = guest_category
                changed = True
            if hasattr(application, "status_reason"):
                application.status_reason = status_reason or ""
                changed = True
            if hasattr(application, "internal_note"):
                application.internal_note = internal_note or ""
                changed = True
            if hasattr(application, "gender"):
                application.gender = gender
                changed = True

            if hasattr(application, "reviewed_by") and request.user:
                application.reviewed_by = request.user
                changed = True

            if changed:
                application.save()
                messages.success(request, _("Application details updated."))
            else:
                messages.info(request, _("Nothing changed."))

        else:
            messages.error(request, _("Unknown action."))

        return HttpResponseRedirect(
            reverse(
                "plugins:pretix_exclusive_access:application_detail",
                kwargs={
                    "organizer": request.organizer.slug,
                    "event": request.event.slug,
                    "application_id": application.pk,
                },
            )
        )
