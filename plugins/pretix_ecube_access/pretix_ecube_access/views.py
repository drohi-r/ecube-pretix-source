import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from pretix.base.models import Event
from pretix.multidomain.urlreverse import build_absolute_uri

from .forms import EcubeAccessDoorForm, ScanTestForm
from .models import EcubeAccessDoor, EcubeAccessScanLog
from .services import process_scan


def _get_event(organizer, event):
    return get_object_or_404(Event, organizer__slug=organizer, slug=event)


def _get_public_door(organizer, event, door_slug, door_token):
    evt = _get_event(organizer, event)
    door = get_object_or_404(
        EcubeAccessDoor,
        event=evt,
        slug=door_slug,
        public_token=door_token,
        is_active=True,
    )
    return evt, door


def _door_relative_path(door):
    return f"access/{door.slug}/{door.public_token}/"


def _door_session_key(door):
    return f"ecube_access_door_auth_{door.pk}"


def _door_session_authenticated(request, door):
    return request.session.get(_door_session_key(door)) == door.current_public_auth_session_value()


def _mark_door_session_authenticated(request, door):
    request.session[_door_session_key(door)] = door.current_public_auth_session_value()
    request.session.modified = True


def _clear_door_session_authenticated(request, door):
    request.session.pop(_door_session_key(door), None)
    request.session.modified = True


def _door_full_url(event, door):
    return build_absolute_uri(
        event,
        "plugins:pretix_ecube_access:public_door_shell",
        kwargs={
            "door_slug": door.slug,
            "door_token": door.public_token,
        },
    )


@login_required
def control_dashboard(request, organizer, event):
    evt = _get_event(organizer, event)
    logs = EcubeAccessScanLog.objects.filter(event=evt).order_by("-scanned_at")[:30]
    doors = EcubeAccessDoor.objects.filter(event=evt).order_by("name")

    context = {
        "event": evt,
        "logs": logs,
        "doors": doors,
        "count_total": EcubeAccessScanLog.objects.filter(event=evt).count(),
        "count_allowed": EcubeAccessScanLog.objects.filter(event=evt, result__in=["allowed", "allowed_exit"]).count(),
        "count_denied": EcubeAccessScanLog.objects.filter(event=evt).exclude(result__in=["allowed", "allowed_exit"]).count(),
    }
    return render(request, "pretix_ecube_access/control_dashboard.html", context)


@login_required
def control_doors_list(request, organizer, event):
    evt = _get_event(organizer, event)
    doors = EcubeAccessDoor.objects.filter(event=evt).order_by("name")

    rows = []
    for d in doors:
        rows.append({
            "door": d,
            "path": _door_relative_path(d),
            "full_url": _door_full_url(evt, d),
        })

    return render(
        request,
        "pretix_ecube_access/control_doors_list.html",
        {
            "event": evt,
            "door_rows": rows,
        },
    )


@login_required
def control_door_create(request, organizer, event):
    evt = _get_event(organizer, event)

    if request.method == "POST":
        form = EcubeAccessDoorForm(request.POST, event=evt)
        if form.is_valid():
            door = form.save(commit=False)
            door.event = evt
            door.public_token = EcubeAccessDoor.generate_token()
            if not (door.public_auth_nonce or "").strip():
                door.rotate_public_auth_nonce()
            door.save()
            messages.success(request, f"Door '{door.name}' created.")
            return redirect(
                "plugins:pretix_ecube_access:control_doors_list",
                organizer=evt.organizer.slug,
                event=evt.slug,
            )
    else:
        form = EcubeAccessDoorForm(event=evt)

    return render(
        request,
        "pretix_ecube_access/control_door_form.html",
        {
            "event": evt,
            "form": form,
            "page_title": "Create door",
            "submit_label": "Create door",
            "door": None,
        },
    )


@login_required
def control_door_edit(request, organizer, event, pk):
    evt = _get_event(organizer, event)
    door = get_object_or_404(EcubeAccessDoor, pk=pk, event=evt)

    if request.method == "POST":
        form = EcubeAccessDoorForm(request.POST, instance=door, event=evt)
        if form.is_valid():
            form.save()
            messages.success(request, f"Door '{door.name}' updated.")
            return redirect(
                "plugins:pretix_ecube_access:control_doors_list",
                organizer=evt.organizer.slug,
                event=evt.slug,
            )
    else:
        form = EcubeAccessDoorForm(instance=door, event=evt)

    return render(
        request,
        "pretix_ecube_access/control_door_form.html",
        {
            "event": evt,
            "form": form,
            "page_title": "Edit door",
            "submit_label": "Save changes",
            "door": door,
            "door_path": _door_relative_path(door),
            "door_full_url": _door_full_url(evt, door),
        },
    )


@login_required
def control_door_regenerate_token(request, organizer, event, pk):
    evt = _get_event(organizer, event)
    door = get_object_or_404(EcubeAccessDoor, pk=pk, event=evt)

    if request.method == "POST":
        door.public_token = EcubeAccessDoor.generate_token()
        door.rotate_public_auth_nonce()
        door.save(update_fields=["public_token", "public_auth_nonce", "updated_at"])
        messages.success(request, f"Door token regenerated for '{door.name}'.")

    return redirect(
        "plugins:pretix_ecube_access:control_door_edit",
        organizer=evt.organizer.slug,
        event=evt.slug,
        pk=door.pk,
    )


@login_required
def control_door_delete(request, organizer, event, pk):
    evt = _get_event(organizer, event)
    door = get_object_or_404(EcubeAccessDoor, pk=pk, event=evt)

    if request.method == "POST":
        confirm_name = (request.POST.get("confirm_name") or "").strip()

        if confirm_name != (door.name or "").strip():
            messages.error(
                request,
                f"Door not deleted. Type the exact door name '{door.name}' to confirm deletion.",
            )
            return render(
                request,
                "pretix_ecube_access/control_door_delete_confirm.html",
                {
                    "event": evt,
                    "door": door,
                    "expected_name": door.name,
                    "door_path": _door_relative_path(door),
                    "door_full_url": _door_full_url(evt, door),
                },
            )

        deleted_name = door.name
        door.delete()
        messages.success(request, f"Door '{deleted_name}' deleted.")
        return redirect(
            "plugins:pretix_ecube_access:control_doors_list",
            organizer=evt.organizer.slug,
            event=evt.slug,
        )

    return render(
        request,
        "pretix_ecube_access/control_door_delete_confirm.html",
        {
            "event": evt,
            "door": door,
            "expected_name": door.name,
            "door_path": _door_relative_path(door),
            "door_full_url": _door_full_url(evt, door),
        },
    )

@login_required
def control_ops_dashboard(request, organizer, event):
    from collections import Counter
    from datetime import timedelta
    from decimal import Decimal
    from django.db.models import Sum
    from django.utils import timezone
    from pretix.base.models import Order, OrderPosition

    def pct(value, total):
        return round((value / total) * 100, 1) if total else 0

    def conic(parts):
        cursor = 0.0
        segments = []
        for color, value in parts:
            if value <= 0:
                continue
            nxt = cursor + value
            segments.append(f"{color} {cursor:.2f}% {nxt:.2f}%")
            cursor = nxt
        if cursor < 100:
            segments.append(f"rgba(255,255,255,.06) {cursor:.2f}% 100%")
        return "conic-gradient(" + ", ".join(segments) + ")"

    evt = _get_event(organizer, event)

    logs_qs = EcubeAccessScanLog.objects.filter(event=evt).order_by("-scanned_at")
    doors = list(EcubeAccessDoor.objects.filter(event=evt).order_by("name"))

    allowed_results = [
        EcubeAccessScanLog.RESULT_ALLOWED,
        EcubeAccessScanLog.RESULT_ALLOWED_EXIT,
    ]

    recent_window = timezone.now() - timedelta(hours=24)
    recent_logs = list(logs_qs.filter(scanned_at__gte=recent_window)[:400])
    logs = list(logs_qs[:32])

    from django.db.models import Count, Q as _Q

    log_agg = logs_qs.aggregate(
        count_total=Count("id"),
        count_allowed=Count("id", filter=_Q(result__in=allowed_results)),
        count_access_pending=Count("id", filter=_Q(result="pending")),
        count_credentials=Count("id", filter=_Q(object_type=EcubeAccessScanLog.TYPE_CREDENTIAL)),
        count_tickets=Count("id", filter=_Q(object_type=EcubeAccessScanLog.TYPE_TICKET)),
    )
    count_total = log_agg["count_total"]
    count_allowed = log_agg["count_allowed"]
    count_access_pending = log_agg["count_access_pending"]
    count_access_blocked = max(count_total - count_allowed - count_access_pending, 0)
    count_denied = count_access_blocked + count_access_pending

    count_credentials = log_agg["count_credentials"]
    count_tickets = log_agg["count_tickets"]
    count_signal_other = max(count_total - count_credentials - count_tickets, 0)

    count_active_doors = sum(1 for d in doors if d.is_active)
    count_protected_doors = sum(1 for d in doors if getattr(d, "has_access_pin", False))

    allowed_rate = pct(count_allowed, count_total)
    denied_rate = pct(count_denied, count_total)

    entry_allowed = logs_qs.filter(
        action=EcubeAccessScanLog.ACTION_ENTRY,
        result=EcubeAccessScanLog.RESULT_ALLOWED,
    ).count()
    exit_allowed = logs_qs.filter(
        action=EcubeAccessScanLog.ACTION_EXIT,
        result=EcubeAccessScanLog.RESULT_ALLOWED_EXIT,
    ).count()
    count_inside_signal = max(entry_allowed - exit_allowed, 0)

    orders_qs = Order.objects.filter(event=evt)
    order_agg = orders_qs.aggregate(
        count_paid_orders=Count("id", filter=_Q(status="p")),
        count_pending_orders=Count("id", filter=_Q(status="n")),
        count_expired_orders=Count("id", filter=_Q(status="e")),
        count_canceled_orders=Count("id", filter=_Q(status="c")),
        gross_paid_raw=Sum("total", filter=_Q(status="p")),
    )
    count_paid_orders = order_agg["count_paid_orders"]
    count_pending_orders = order_agg["count_pending_orders"]
    count_expired_orders = order_agg["count_expired_orders"]
    count_canceled_orders = order_agg["count_canceled_orders"]

    gross_paid_raw = order_agg["gross_paid_raw"] or Decimal("0.00")
    gross_paid = f"{gross_paid_raw:.2f}"

    count_paid_positions = OrderPosition.objects.filter(order__event=evt, order__status="p").count()
    count_checked_in_positions = OrderPosition.objects.filter(
        order__event=evt,
        order__status="p",
        all_checkins__isnull=False,
    ).distinct().count()
    checked_in_rate = pct(count_checked_in_positions, count_paid_positions)

    order_mix_total = count_paid_orders + count_pending_orders + count_expired_orders + count_canceled_orders
    order_pct_paid = pct(count_paid_orders, order_mix_total)
    order_pct_pending = pct(count_pending_orders, order_mix_total)
    order_pct_expired = pct(count_expired_orders, order_mix_total)
    order_pct_canceled = pct(count_canceled_orders, order_mix_total)

    access_mix_total = count_allowed + count_access_pending + count_access_blocked
    access_pct_allowed = pct(count_allowed, access_mix_total)
    access_pct_pending = pct(count_access_pending, access_mix_total)
    access_pct_blocked = pct(count_access_blocked, access_mix_total)

    signal_mix_total = count_credentials + count_tickets + count_signal_other
    signal_pct_credentials = pct(count_credentials, signal_mix_total)
    signal_pct_tickets = pct(count_tickets, signal_mix_total)
    signal_pct_other = pct(count_signal_other, signal_mix_total)

    order_mix_style = conic([
        ("#2ecc71", order_pct_paid),
        ("#ffb84d", order_pct_pending),
        ("#5caeff", order_pct_expired),
        ("#ed1c24", order_pct_canceled),
    ])

    access_mix_style = conic([
        ("#2ecc71", access_pct_allowed),
        ("#5caeff", access_pct_pending),
        ("#ed1c24", access_pct_blocked),
    ])

    signal_mix_style = conic([
        ("#a86cff", signal_pct_credentials),
        ("#5caeff", signal_pct_tickets),
        ("#7f8ea3", signal_pct_other),
    ])

    anomaly_counter = Counter()
    anomaly_message_counter = Counter()
    for log in recent_logs:
        if log.result not in allowed_results:
            anomaly_counter[log.result or "unknown"] += 1
            anomaly_message_counter[(log.result or "unknown", log.message or "No detail returned.")] += 1

    anomaly_rows = []
    for (result, message), qty in anomaly_message_counter.most_common(8):
        anomaly_rows.append({
            "result": result,
            "message": message,
            "qty": qty,
            "label": (result or "unknown").replace("_", " ").title(),
        })

    top_anomaly = anomaly_rows[0]["label"] if anomaly_rows else "Clear"

    door_rows = []
    for door in doors:
        door_logs = [
            log for log in recent_logs
            if (log.gate or "").strip() in {door.slug, door.name}
        ]
        last_scan = door_logs[0] if door_logs else None
        blocked_24h = sum(1 for log in door_logs if log.result not in allowed_results)

        door_rows.append({
            "door": door,
            "full_url": _door_full_url(evt, door),
            "path": _door_relative_path(door),
            "scans_24h": len(door_logs),
            "blocked_24h": blocked_24h,
            "allowed_24h": max(len(door_logs) - blocked_24h, 0),
            "last_scan": last_scan,
        })

    door_rows.sort(
        key=lambda row: (
            not row["door"].is_active,
            -row["scans_24h"],
            row["door"].name.lower(),
        )
    )

    primary_door = door_rows[0] if door_rows else None
    secondary_doors = door_rows[1:8] if len(door_rows) > 1 else []

    recent_credential_logs = [log for log in logs if log.object_type == EcubeAccessScanLog.TYPE_CREDENTIAL][:5]
    recent_ticket_logs = [log for log in logs if log.object_type == EcubeAccessScanLog.TYPE_TICKET][:5]

    base_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
    hourly_scan_bars = []
    for offset in range(11, -1, -1):
        start = base_hour - timedelta(hours=offset)
        end = start + timedelta(hours=1)
        qty = sum(1 for log in recent_logs if start <= log.scanned_at < end)
        hourly_scan_bars.append({
            "label": start.strftime("%H"),
            "count": qty,
        })

    max_hourly_scan = max([row["count"] for row in hourly_scan_bars] or [0])
    for row in hourly_scan_bars:
        if max_hourly_scan and row["count"]:
            row["height"] = max(12, round((row["count"] / max_hourly_scan) * 100))
        else:
            row["height"] = 0

    alert_state = "Secure"
    if count_access_blocked > count_allowed:
        alert_state = "Critical"
    elif count_denied:
        alert_state = "Attention"

    context = {
        "event": evt,
        "logs": logs,
        "primary_door": primary_door,
        "secondary_doors": secondary_doors,
        "count_total": count_total,
        "count_allowed": count_allowed,
        "count_denied": count_denied,
        "count_access_pending": count_access_pending,
        "count_access_blocked": count_access_blocked,
        "count_credentials": count_credentials,
        "count_tickets": count_tickets,
        "count_signal_other": count_signal_other,
        "count_active_doors": count_active_doors,
        "count_protected_doors": count_protected_doors,
        "count_inside_signal": count_inside_signal,
        "allowed_rate": allowed_rate,
        "denied_rate": denied_rate,
        "alert_state": alert_state,
        "top_anomaly": top_anomaly,
        "anomaly_rows": anomaly_rows,
        "recent_credential_logs": recent_credential_logs,
        "recent_ticket_logs": recent_ticket_logs,
        "kiosk_mode": request.GET.get("kiosk") == "1",

        "count_paid_orders": count_paid_orders,
        "count_pending_orders": count_pending_orders,
        "count_expired_orders": count_expired_orders,
        "count_canceled_orders": count_canceled_orders,
        "gross_paid": gross_paid,
        "count_paid_positions": count_paid_positions,
        "count_checked_in_positions": count_checked_in_positions,
        "checked_in_rate": checked_in_rate,

        "order_pct_paid": order_pct_paid,
        "order_pct_pending": order_pct_pending,
        "order_pct_expired": order_pct_expired,
        "order_pct_canceled": order_pct_canceled,
        "access_pct_allowed": access_pct_allowed,
        "access_pct_pending": access_pct_pending,
        "access_pct_blocked": access_pct_blocked,
        "signal_pct_credentials": signal_pct_credentials,
        "signal_pct_tickets": signal_pct_tickets,
        "signal_pct_other": signal_pct_other,

        "order_mix_style": order_mix_style,
        "access_mix_style": access_mix_style,
        "signal_mix_style": signal_mix_style,
        "hourly_scan_bars": hourly_scan_bars,
    }
    return render(request, "pretix_ecube_access/control_ops_dashboard.html", context)





@login_required
def control_scan_shell(request, organizer, event):
    evt = _get_event(organizer, event)
    result = None

    if request.method == "POST":
        form = ScanTestForm(request.POST)
        if form.is_valid():
            try:
                result = process_scan(
                    event=evt,
                    payload=form.cleaned_data["payload"],
                    action=form.cleaned_data.get("action") or "entry",
                    gate=form.cleaned_data.get("gate") or "",
                    operator_name=form.cleaned_data.get("operator_name") or "",
                    device_id=form.cleaned_data.get("device_id") or "",
                )
            except Exception as exc:
                result = {
                    "ok": False,
                    "result": "error",
                    "engine": "ecube_access",
                    "object_type": "unknown",
                    "display_name": "",
                    "display_type": "Unknown",
                    "code": form.cleaned_data.get("payload") or "",
                    "photo_url": None,
                    "message": f"Unhandled scan shell error: {exc}",
                    "gate": form.cleaned_data.get("gate") or "",
                    "timestamp": "",
                    "meta": {"action": form.cleaned_data.get("action") or "entry"},
                }
    else:
        form = ScanTestForm()

    return render(
        request,
        "pretix_ecube_access/control_scan_shell.html",
        {
            "event": evt,
            "form": form,
            "result": result,
        },
    )


@login_required
def control_scan_logs(request, organizer, event):
    evt = _get_event(organizer, event)
    logs = EcubeAccessScanLog.objects.filter(event=evt).order_by("-scanned_at")[:200]
    return render(
        request,
        "pretix_ecube_access/control_scan_logs.html",
        {
            "event": evt,
            "logs": logs,
        },
    )


@login_required
def control_door_shell(request, organizer, event):
    evt = _get_event(organizer, event)
    return render(
        request,
        "pretix_ecube_access/pwa_scanner_shell.html",
        {
            "event": evt,
            "door_name": "Control Door",
            "default_action": "entry",
            "is_public_door": False,
        },
    )


def public_door_shell(request, organizer, event, door_slug, door_token):
    evt, door = _get_public_door(organizer, event, door_slug, door_token)

    if door.has_access_pin and not _door_session_authenticated(request, door):
        pin_error = None

        if request.method == "POST":
            submitted_pin = (request.POST.get("door_pin") or "").strip()
            if door.check_access_pin(submitted_pin):
                _mark_door_session_authenticated(request, door)
                return redirect(
                    "plugins:pretix_ecube_access:public_door_shell",
                    organizer=evt.organizer.slug,
                    event=evt.slug,
                    door_slug=door.slug,
                    door_token=door.public_token,
                )
            pin_error = "Incorrect door PIN/password."

        return render(
            request,
            "pretix_ecube_access/public_door_unlock.html",
            {
                "event": evt,
                "door_name": door.name,
                "default_action": door.default_action,
                "is_public_door": True,
                "public_door": door,
                "pin_error": pin_error,
            },
        )

    return render(
        request,
        "pretix_ecube_access/public_door_shell.html",
        {
            "event": evt,
            "door_name": door.name,
            "door_slug": door.slug,
            "door_token": door.public_token,
            "default_action": door.default_action,
            "is_public_door": True,
            "public_door": door,
            "door_pin_enabled": door.has_access_pin,
        },
    )


@csrf_exempt
@require_POST
def public_api_scan(request, organizer, event, door_slug, door_token):
    evt, door = _get_public_door(organizer, event, door_slug, door_token)

    if door.has_access_pin and not _door_session_authenticated(request, door):
        return JsonResponse(
            {"ok": False, "result": "denied", "message": "Door PIN/password required before scanning is allowed."},
            status=403,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "result": "error", "message": "Invalid JSON body"}, status=400)

    try:
        response = process_scan(
            event=evt,
            payload=payload.get("payload") or "",
            action=payload.get("action") or door.default_action or "entry",
            gate=payload.get("gate") or door.slug,
            operator_name=payload.get("operator_name") or "",
            device_id=payload.get("device_id") or "",
        )
        return JsonResponse(
            response,
            status=200,
        )
    except Exception as exc:
        return JsonResponse(
            {"ok": False, "result": "error", "message": f"Unhandled public API scan error: {exc}"},
            status=500,
        )

@csrf_exempt
@require_POST
@login_required
def api_scan(request, organizer, event):
    evt = _get_event(organizer, event)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse(
            {"ok": False, "result": "error", "message": "Invalid JSON body"},
            status=400,
        )

    try:
        response = process_scan(
            event=evt,
            payload=payload.get("payload") or "",
            action=payload.get("action") or "entry",
            gate=payload.get("gate") or "",
            operator_name=payload.get("operator_name") or "",
            device_id=payload.get("device_id") or "",
        )
        return JsonResponse(response)
    except Exception as exc:
        return JsonResponse(
            {"ok": False, "result": "error", "message": f"Unhandled API scan error: {exc}"},
            status=500,
        )


def public_door_lock(request, organizer, event, door_slug, door_token):
    evt, door = _get_public_door(organizer, event, door_slug, door_token)
    _clear_door_session_authenticated(request, door)
    return redirect(
        "plugins:pretix_ecube_access:public_door_shell",
        organizer=evt.organizer.slug,
        event=evt.slug,
        door_slug=door.slug,
        door_token=door.public_token,
    )


