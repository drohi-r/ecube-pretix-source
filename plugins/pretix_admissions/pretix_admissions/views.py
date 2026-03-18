from datetime import timedelta, datetime, time as dt_time
import csv
import base64
from io import BytesIO

import qrcode
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.urls import reverse
from pretix.base.models import Event

from .forms import (
    BulkCredentialImportForm,
    AdmissionCredentialForm,
    RevokeCredentialForm,
    CredentialsSettingsForm,
    CREDENTIAL_FIELD_SPECS,
    get_credential_form_config,
    get_credential_design_config,
)
from .models import AdmissionCredential
from .services import (
    issue_credential,
    mark_credential_blocked,
    mark_credential_revoked,
    reactivate_credential,
)


def _get_event(organizer, event):
    return get_object_or_404(Event, organizer__slug=organizer, slug=event)


def _get_credential(organizer, event, pk):
    evt = _get_event(organizer, event)
    cred = get_object_or_404(AdmissionCredential, pk=pk, event=evt)
    return evt, cred


def _credential_qr_payload(credential):
    return f"ECA:CRED:{credential.qr_token}"


def _qr_data_uri(payload):
    qr = qrcode.QRCode(box_size=6, border=1)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"



def _credentials_dashboard_context(evt, filtered_qs, request):
    base_qs = AdmissionCredential.objects.filter(event=evt)
    now = timezone.now()
    soon = now + timedelta(days=2)

    shown_count = filtered_qs.count()
    total_all = base_qs.count()

    active_count = filtered_qs.filter(status=AdmissionCredential.STATUS_ACTIVE).count()
    used_count = filtered_qs.filter(status=AdmissionCredential.STATUS_USED).count()
    blocked_count = filtered_qs.filter(status=AdmissionCredential.STATUS_BLOCKED).count()
    revoked_count = filtered_qs.filter(status=AdmissionCredential.STATUS_REVOKED).count()
    expired_count = filtered_qs.filter(status=AdmissionCredential.STATUS_EXPIRED).count()

    inside_count = filtered_qs.filter(is_inside=True).count()
    recent_scanned_count = filtered_qs.filter(last_scanned_at__gte=now - timedelta(days=1)).count()
    missing_photo_count = filtered_qs.filter(Q(holder_photo="") | Q(holder_photo__isnull=True)).count()
    expiring_soon_count = filtered_qs.filter(
        valid_until__isnull=False,
        valid_until__gte=now,
        valid_until__lte=soon,
    ).count()

    status_labels = dict(AdmissionCredential.STATUS_CHOICES)
    type_labels = dict(AdmissionCredential.TYPE_CHOICES)

    status_rows = [
        {
            "value": row["status"] or "",
            "label": status_labels.get(row["status"], row["status"] or "—"),
            "count": row["total"],
        }
        for row in filtered_qs.values("status").annotate(total=Count("id")).order_by("-total", "status")
    ]

    type_rows = [
        {
            "value": row["credential_type"] or "",
            "label": type_labels.get(row["credential_type"], row["credential_type"] or "—"),
            "count": row["total"],
        }
        for row in filtered_qs.values("credential_type").annotate(total=Count("id")).order_by("-total", "credential_type")
    ]

    recent_credentials = list(filtered_qs[:5])

    return {
        "shown_count": shown_count,
        "total_all": total_all,
        "filters_active": bool(
            (request.GET.get("q") or "").strip()
            or (request.GET.get("status") or "").strip()
            or (request.GET.get("credential_type") or "").strip()
            or (request.GET.get("inside") or "").strip()
        ),
        "active_count": active_count,
        "used_count": used_count,
        "blocked_count": blocked_count,
        "revoked_count": revoked_count,
        "expired_count": expired_count,
        "inside_count": inside_count,
        "recent_scanned_count": recent_scanned_count,
        "missing_photo_count": missing_photo_count,
        "expiring_soon_count": expiring_soon_count,
        "status_rows": status_rows,
        "type_rows": type_rows,
        "recent_credentials": recent_credentials,
    }



class CredentialsSettingsForm(forms.Form):
    print_template = forms.ChoiceField(
        required=True,
        choices=(
            ("standard", "Standard badge"),
            ("compact", "Compact badge"),
            ("photo_focus", "Photo focus badge"),
        ),
        label="Print template",
    )
    primary_color = forms.CharField(required=False, label="Primary color")
    accent_color = forms.CharField(required=False, label="Accent color")

    show_holder_email = forms.BooleanField(required=False, label="Show email")
    show_holder_phone = forms.BooleanField(required=False, label="Show phone")
    show_holder_photo = forms.BooleanField(required=False, label="Show photo")
    show_credential_type = forms.BooleanField(required=False, label="Show credential type")
    show_entry_mode = forms.BooleanField(required=False, label="Show entry mode")
    show_label = forms.BooleanField(required=False, label="Show label")
    show_notes = forms.BooleanField(required=False, label="Show notes")
    show_valid_from = forms.BooleanField(required=False, label="Show valid from")
    show_valid_until = forms.BooleanField(required=False, label="Show valid until")

    require_holder_email = forms.BooleanField(required=False, label="Require email")
    require_holder_phone = forms.BooleanField(required=False, label="Require phone")
    require_holder_photo = forms.BooleanField(required=False, label="Require photo")
    require_credential_type = forms.BooleanField(required=False, label="Require credential type")
    require_entry_mode = forms.BooleanField(required=False, label="Require entry mode")
    require_label = forms.BooleanField(required=False, label="Require label")
    require_notes = forms.BooleanField(required=False, label="Require notes")
    require_valid_from = forms.BooleanField(required=False, label="Require valid from")
    require_valid_until = forms.BooleanField(required=False, label="Require valid until")

    print_holder_email = forms.BooleanField(required=False, label="Print email")
    print_holder_phone = forms.BooleanField(required=False, label="Print phone")
    print_holder_photo = forms.BooleanField(required=False, label="Print photo")
    print_credential_type = forms.BooleanField(required=False, label="Print credential type")
    print_entry_mode = forms.BooleanField(required=False, label="Print entry mode")
    print_label = forms.BooleanField(required=False, label="Print label")
    print_notes = forms.BooleanField(required=False, label="Print notes")
    print_valid_from = forms.BooleanField(required=False, label="Print valid from")
    print_valid_until = forms.BooleanField(required=False, label="Print valid until")


@login_required
def control_credentials_settings(request, organizer, event):
    evt = _get_event(organizer, event)

    field_specs = [
        ("holder_email", "Email"),
        ("holder_phone", "Phone"),
        ("holder_photo", "Photo"),
        ("credential_type", "Credential type"),
        ("entry_mode", "Entry mode"),
        ("label", "Label"),
        ("notes", "Notes"),
        ("valid_from", "Valid from"),
        ("valid_until", "Valid until"),
    ]

    initial = {
        "print_template": evt.settings.get("admissions_print_template", default="standard") or "standard",
        "primary_color": evt.settings.get("admissions_primary_color", default="#ED1C24") or "#ED1C24",
        "accent_color": evt.settings.get("admissions_accent_color", default="#F0EDE8") or "#F0EDE8",
    }

    default_show = {
        "holder_email": True,
        "holder_phone": True,
        "holder_photo": True,
        "credential_type": True,
        "entry_mode": True,
        "label": True,
        "notes": True,
        "valid_from": True,
        "valid_until": True,
    }
    default_require = {
        "holder_email": False,
        "holder_phone": False,
        "holder_photo": False,
        "credential_type": True,
        "entry_mode": True,
        "label": False,
        "notes": False,
        "valid_from": False,
        "valid_until": False,
    }
    default_print = {
        "holder_email": True,
        "holder_phone": False,
        "holder_photo": True,
        "credential_type": True,
        "entry_mode": True,
        "label": True,
        "notes": False,
        "valid_from": False,
        "valid_until": True,
    }

    for key, _label in field_specs:
        initial[f"show_{key}"] = evt.settings.get(f"admissions_show_{key}", as_type=bool, default=default_show[key])
        initial[f"require_{key}"] = evt.settings.get(f"admissions_require_{key}", as_type=bool, default=default_require[key])
        initial[f"print_{key}"] = evt.settings.get(f"admissions_print_{key}", as_type=bool, default=default_print[key])

    if request.method == "POST":
        form = CredentialsSettingsForm(request.POST, initial=initial)
        if form.is_valid():
            evt.settings.set("admissions_print_template", form.cleaned_data.get("print_template") or "standard")
            evt.settings.set("admissions_primary_color", form.cleaned_data.get("primary_color") or "#ED1C24")
            evt.settings.set("admissions_accent_color", form.cleaned_data.get("accent_color") or "#F0EDE8")

            for key, _label in field_specs:
                show = bool(form.cleaned_data.get(f"show_{key}"))
                require = bool(form.cleaned_data.get(f"require_{key}")) if show else False
                include_print = bool(form.cleaned_data.get(f"print_{key}")) if show else False

                evt.settings.set(f"admissions_show_{key}", show)
                evt.settings.set(f"admissions_require_{key}", require)
                evt.settings.set(f"admissions_print_{key}", include_print)

            messages.success(request, "Credential settings saved.")
            return redirect(
                "plugins:pretix_admissions:control_credentials_settings",
                organizer=evt.organizer.slug,
                event=evt.slug,
            )
    else:
        form = CredentialsSettingsForm(initial=initial)

    field_rows = []
    for key, label in field_specs:
        field_rows.append(
            {
                "label": label,
                "show_field": form[f"show_{key}"],
                "require_field": form[f"require_{key}"],
                "print_field": form[f"print_{key}"],
            }
        )

    return render(
        request,
        "pretix_admissions/control_credentials_settings.html",
        {
            "event": evt,
            "form": form,
            "field_rows": field_rows,
        },
    )



def _credentials_filtered_queryset(evt, request):
    q = (request.POST.get("q") or request.GET.get("q") or "").strip()
    status = (request.POST.get("status") or request.GET.get("status") or "").strip()
    credential_type = (request.POST.get("credential_type") or request.GET.get("credential_type") or "").strip()
    inside = (request.POST.get("inside") or request.GET.get("inside") or "").strip()

    qs = AdmissionCredential.objects.filter(event=evt)

    if q:
        qs = qs.filter(
            Q(credential_code__icontains=q)
            | Q(holder_name__icontains=q)
            | Q(holder_email__icontains=q)
            | Q(holder_phone__icontains=q)
            | Q(label__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    if credential_type:
        qs = qs.filter(credential_type=credential_type)

    if inside == "inside":
        qs = qs.filter(is_inside=True)
    elif inside == "outside":
        qs = qs.filter(is_inside=False)

    return {
        "q": q,
        "status": status,
        "credential_type": credential_type,
        "inside": inside,
        "qs": qs.order_by("-created_at"),
    }


def _credentials_csv_response(evt, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="credentials-{evt.slug}-{timezone.now().strftime("%Y%m%d-%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "credential_code",
        "holder_name",
        "credential_type",
        "status",
        "entry_mode",
        "is_inside",
        "holder_email",
        "holder_phone",
        "label",
        "scan_count",
        "last_scanned_at",
        "last_scanned_gate",
        "valid_from",
        "valid_until",
        "issued_at",
    ])

    for cred in queryset:
        writer.writerow([
            cred.credential_code,
            cred.holder_name,
            cred.credential_type,
            cred.status,
            cred.entry_mode,
            "yes" if cred.is_inside else "no",
            cred.holder_email or "",
            cred.holder_phone or "",
            cred.label or "",
            cred.scan_count,
            cred.last_scanned_at.isoformat() if cred.last_scanned_at else "",
            cred.last_scanned_gate or "",
            cred.valid_from.date().isoformat() if cred.valid_from else "",
            cred.valid_until.date().isoformat() if cred.valid_until else "",
            cred.issued_at.isoformat() if cred.issued_at else "",
        ])
    return response


@login_required
def control_credentials_list(request, organizer, event):
    evt = _get_event(organizer, event)
    state = _credentials_filtered_queryset(evt, request)

    q = state["q"]
    status = state["status"]
    credential_type = state["credential_type"]
    inside = state["inside"]
    qs = state["qs"]

    if request.method == "POST":
        action = (request.POST.get("bulk_action") or "").strip()
        apply_to_filtered = bool(request.POST.get("apply_to_filtered"))
        selected_ids = []
        for raw in request.POST.getlist("selected_credentials"):
            raw = (raw or "").strip()
            if raw.isdigit():
                selected_ids.append(int(raw))

        target_qs = qs if apply_to_filtered else qs.filter(pk__in=selected_ids)
        count = target_qs.count()

        if not action:
            messages.warning(request, "Choose a bulk action first.")
        elif count == 0:
            messages.warning(request, "No credentials selected.")
        elif action == "export_csv":
            return _credentials_csv_response(evt, target_qs)
        elif action == "block":
            processed = 0
            for cred in target_qs:
                mark_credential_blocked(credential=cred)
                processed += 1
            messages.success(request, f"{processed} credential(s) blocked.")
        elif action == "reactivate":
            processed = 0
            for cred in target_qs:
                reactivate_credential(credential=cred)
                processed += 1
            messages.success(request, f"{processed} credential(s) reactivated.")
        elif action == "revoke":
            reason = (request.POST.get("bulk_reason") or "").strip()
            processed = 0
            for cred in target_qs:
                mark_credential_revoked(
                    credential=cred,
                    user=request.user,
                    reason=reason,
                )
                processed += 1
            messages.success(request, f"{processed} credential(s) revoked.")
        else:
            messages.warning(request, "Unknown bulk action.")

        return redirect(
            "plugins:pretix_admissions:control_credentials_list",
            organizer=evt.organizer.slug,
            event=evt.slug,
        )

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "event": evt,
        "page_obj": page,
        "credentials": page.object_list,
        "q": q,
        "status_filter": status,
        "type_filter": credential_type,
        "inside_filter": inside,
        "status_choices": AdmissionCredential.STATUS_CHOICES,
        "type_choices": AdmissionCredential.TYPE_CHOICES,
        "dashboard": _credentials_dashboard_context(evt, qs, request),
    }
    return render(request, "pretix_admissions/control_credentials_list.html", context)



def _bulk_import_allowed_headers():
    return [
        "holder_name",
        "credential_type",
        "entry_mode",
        "holder_email",
        "holder_phone",
        "label",
        "notes",
        "valid_from",
        "valid_until",
    ]


@login_required
def control_credentials_import_sample(request, organizer, event):
    evt = _get_event(organizer, event)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="credentials-import-sample-{evt.slug}.csv"'
    writer = csv.writer(response)
    writer.writerow(_bulk_import_allowed_headers())
    writer.writerow([
        "Sample Vendor",
        AdmissionCredential.TYPE_VENDOR,
        AdmissionCredential.ENTRY_MODE_REENTRY_AFTER_EXIT,
        "vendor@example.com",
        "01700000000",
        "Vendor team",
        "Imported from CSV",
        "",
        "",
    ])
    writer.writerow([
        "Sample VIP",
        AdmissionCredential.TYPE_VIP,
        AdmissionCredential.ENTRY_MODE_SINGLE,
        "vip@example.com",
        "01800000000",
        "VIP Guest",
        "",
        "",
        "",
    ])
    return response


@login_required
def control_credentials_import(request, organizer, event):
    evt = _get_event(organizer, event)
    form = BulkCredentialImportForm(request.POST or None, request.FILES or None)

    preview_rows = []
    import_errors = []
    imported_count = 0
    allowed_headers = _bulk_import_allowed_headers()

    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["csv_file"]
        try:
            raw = upload.read()
            decoded = raw.decode("utf-8-sig")
        except Exception:
            decoded = ""
            import_errors.append("Could not read the uploaded CSV. Use UTF-8 CSV format.")

        parsed_rows = []
        if decoded:
            reader = csv.DictReader(io.StringIO(decoded))
            headers = [((h or "").strip()) for h in (reader.fieldnames or []) if (h or "").strip()]
            if not headers:
                import_errors.append("CSV appears to be empty or missing a header row.")
            elif "holder_name" not in headers:
                import_errors.append("CSV must include a holder_name column.")

            type_values = {value for value, _ in AdmissionCredential.TYPE_CHOICES}
            entry_values = {value for value, _ in AdmissionCredential.ENTRY_MODE_CHOICES}

            if not import_errors:
                for index, row in enumerate(reader, start=2):
                    clean = {}
                    for key, value in (row or {}).items():
                        key = (key or "").strip()
                        if not key:
                            continue
                        clean[key] = (value or "").strip()

                    if not any(clean.values()):
                        continue

                    holder_name = clean.get("holder_name", "")
                    credential_type = clean.get("credential_type") or AdmissionCredential.TYPE_GUEST
                    entry_mode = clean.get("entry_mode") or ""
                    holder_email = clean.get("holder_email") or ""
                    holder_phone = clean.get("holder_phone") or ""
                    label = clean.get("label") or ""
                    notes = clean.get("notes") or ""
                    valid_from_raw = clean.get("valid_from") or ""
                    valid_until_raw = clean.get("valid_until") or ""

                    if not holder_name:
                        import_errors.append(f"Row {index}: holder_name is required.")

                    if credential_type not in type_values:
                        import_errors.append(f"Row {index}: invalid credential_type '{credential_type}'.")

                    if entry_mode and entry_mode not in entry_values:
                        import_errors.append(f"Row {index}: invalid entry_mode '{entry_mode}'.")

                    valid_from = None
                    valid_until = None

                    if valid_from_raw:
                        valid_from = parse_datetime(valid_from_raw)
                        if not valid_from:
                            import_errors.append(f"Row {index}: invalid valid_from '{valid_from_raw}'. Use ISO format like 2026-03-18 18:30:00 or 2026-03-18T18:30:00.")

                    if valid_until_raw:
                        valid_until = parse_datetime(valid_until_raw)
                        if not valid_until:
                            import_errors.append(f"Row {index}: invalid valid_until '{valid_until_raw}'. Use ISO format like 2026-03-18 18:30:00 or 2026-03-18T18:30:00.")

                    parsed_rows.append({
                        "row_number": index,
                        "holder_name": holder_name,
                        "credential_type": credential_type,
                        "entry_mode": entry_mode or "(auto)",
                        "holder_email": holder_email,
                        "holder_phone": holder_phone,
                        "label": label,
                        "notes": notes,
                        "_entry_mode_value": entry_mode,
                        "_valid_from_value": valid_from,
                        "_valid_until_value": valid_until,
                    })

            preview_rows = parsed_rows[:100]

            if parsed_rows and not import_errors and form.cleaned_data.get("commit_now"):
                for row in parsed_rows:
                    issue_credential(
                        event=evt,
                        holder_name=row["holder_name"],
                        holder_email=row["holder_email"],
                        holder_phone=row["holder_phone"],
                        credential_type=row["credential_type"] or AdmissionCredential.TYPE_GUEST,
                        entry_mode=row["_entry_mode_value"] or "",
                        label=row["label"],
                        notes=row["notes"],
                        valid_from=row["_valid_from_value"],
                        valid_until=row["_valid_until_value"],
                        issued_by=request.user,
                    )
                    imported_count += 1

                messages.success(request, f"{imported_count} credential(s) imported successfully.")
                return redirect(
                    "plugins:pretix_admissions:control_credentials_list",
                    organizer=evt.organizer.slug,
                    event=evt.slug,
                )

            if parsed_rows and not import_errors and not form.cleaned_data.get("commit_now"):
                messages.success(request, f"CSV validated successfully. {len(parsed_rows)} row(s) ready to import. Re-upload with 'Import immediately' checked to create them.")

    return render(
        request,
        "pretix_admissions/control_credentials_import.html",
        {
            "event": evt,
            "form": form,
            "preview_rows": preview_rows,
            "import_errors": import_errors,
            "allowed_headers": allowed_headers,
        },
    )


@login_required
def control_credential_create(request, organizer, event):
    evt = _get_event(organizer, event)

    if request.method == "POST":
        form = AdmissionCredentialForm(request.POST, request.FILES, event=evt)
        if form.is_valid():
            cleaned = form.cleaned_data
            credential = issue_credential(
                event=evt,
                holder_name=cleaned["holder_name"],
                holder_email=cleaned.get("holder_email") or "",
                holder_phone=cleaned.get("holder_phone") or "",
                credential_type=cleaned.get("credential_type") or AdmissionCredential.TYPE_GUEST,
                entry_mode=cleaned.get("entry_mode") or "",
                label=cleaned.get("label") or "",
                notes=cleaned.get("notes") or "",
                valid_from=cleaned.get("valid_from"),
                valid_until=cleaned.get("valid_until"),
                holder_photo=cleaned.get("holder_photo"),
                issued_by=request.user,
            )
            messages.success(request, f"Credential {credential.credential_code} created.")
            return redirect(
                "plugins:pretix_admissions:control_credential_detail",
                organizer=evt.organizer.slug,
                event=evt.slug,
                pk=credential.pk,
            )
    else:
        form = AdmissionCredentialForm(event=evt)

    return render(
        request,
        "pretix_admissions/control_credential_create.html",
        {
            "event": evt,
            "form": form,
        },
    )


@login_required
def control_credential_detail(request, organizer, event, pk):
    evt, credential = _get_credential(organizer, event, pk)

    if request.method == "POST":
        form = AdmissionCredentialForm(request.POST, request.FILES, instance=credential, event=evt)
        if form.is_valid():
            form.save()
            messages.success(request, "Credential updated.")
            return redirect(
                "plugins:pretix_admissions:control_credential_detail",
                organizer=evt.organizer.slug,
                event=evt.slug,
                pk=credential.pk,
            )
    else:
        form = AdmissionCredentialForm(instance=credential, event=evt)

    revoke_form = RevokeCredentialForm()

    return render(
        request,
        "pretix_admissions/control_credential_detail.html",
        {
            "event": evt,
            "credential": credential,
            "form": form,
            "revoke_form": revoke_form,
            "scan_events": credential.scan_events.all()[:50],
        },
    )



def _credential_print_runtime(evt):
    try:
        from .forms import get_credential_form_config, get_credential_design_config
        print_config = get_credential_form_config(evt)
        design = get_credential_design_config(evt)
    except Exception:
        print_config = {
            "holder_email": {"show": True, "required": False, "include_print": True},
            "holder_phone": {"show": True, "required": False, "include_print": False},
            "holder_photo": {"show": True, "required": False, "include_print": True},
            "credential_type": {"show": True, "required": True, "include_print": True},
            "entry_mode": {"show": True, "required": True, "include_print": True},
            "label": {"show": True, "required": False, "include_print": True},
            "notes": {"show": True, "required": False, "include_print": False},
            "valid_from": {"show": True, "required": False, "include_print": False},
            "valid_until": {"show": True, "required": False, "include_print": True},
        }
        design = {
            "print_template": "standard",
            "primary_color": "#ED1C24",
            "accent_color": "#F0EDE8",
        }
    return {
        "print_config": print_config,
        "design": design,
    }


@login_required
def control_credential_print(request, organizer, event, pk):
    evt, credential = _get_credential(organizer, event, pk)
    qr_payload = _credential_qr_payload(credential)
    qr_data_uri = _qr_data_uri(qr_payload)

    holder_photo_data_uri = ""
    if getattr(credential, "holder_photo", None):
        try:
            import base64
            with credential.holder_photo.open("rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            ext = (credential.holder_photo.name.rsplit(".", 1)[-1] or "png").lower()
            mime = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
                "gif": "image/gif",
            }.get(ext, "image/png")
            holder_photo_data_uri = f"data:{mime};base64,{encoded}"
        except Exception:
            holder_photo_data_uri = ""

    runtime = _credential_print_runtime(evt)

    return render(
        request,
        "pretix_admissions/credential_print.html",
        {
            "event": evt,
            "credential": credential,
            "qr_payload": qr_payload,
            "qr_data_uri": qr_data_uri,
            "holder_photo_data_uri": holder_photo_data_uri,
            "print_config": runtime["print_config"],
            "design": runtime["design"],
        },
    )


@login_required
def control_credential_revoke(request, organizer, event, pk):
    evt, credential = _get_credential(organizer, event, pk)
    if request.method == "POST":
        form = RevokeCredentialForm(request.POST)
        if form.is_valid():
            mark_credential_revoked(
                credential=credential,
                user=request.user,
                reason=form.cleaned_data.get("reason") or "",
            )
            messages.success(request, f"Credential {credential.credential_code} revoked.")
    return redirect(
        "plugins:pretix_admissions:control_credential_detail",
        organizer=evt.organizer.slug,
        event=evt.slug,
        pk=credential.pk,
    )


@login_required
def control_credential_block(request, organizer, event, pk):
    evt, credential = _get_credential(organizer, event, pk)
    if request.method == "POST":
        mark_credential_blocked(credential=credential)
        messages.success(request, f"Credential {credential.credential_code} blocked.")
    return redirect(
        "plugins:pretix_admissions:control_credential_detail",
        organizer=evt.organizer.slug,
        event=evt.slug,
        pk=credential.pk,
    )


@login_required
def control_credential_reactivate(request, organizer, event, pk):
    evt, credential = _get_credential(organizer, event, pk)
    if request.method == "POST":
        reactivate_credential(credential=credential)
        messages.success(request, f"Credential {credential.credential_code} reactivated.")
    return redirect(
        "plugins:pretix_admissions:control_credential_detail",
        organizer=evt.organizer.slug,
        event=evt.slug,
        pk=credential.pk,
    )

