import logging
import os

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

from pretix_admissions.models import AdmissionCredential
from pretix_admissions.services import record_scan_event, validate_credential_token
from pretix_exclusive_access.models import ExclusiveAccessApplication
from .models import EcubeAccessScanLog


def _clean_payload(payload: str) -> str:
    payload = (payload or "").strip()
    if payload.startswith("<") and payload.endswith(">"):
        payload = payload[1:-1].strip()
    return payload


def _clean_token(token: str) -> str:
    token = (token or "").strip()
    if token.startswith("<") and token.endswith(">"):
        token = token[1:-1].strip()
    return token


def classify_payload(payload: str) -> dict:
    payload = _clean_payload(payload)

    if payload.startswith("ECA:CRED:"):
        token = payload.replace("ECA:CRED:", "", 1).strip()
        token = _clean_token(token)
        return {
            "engine": EcubeAccessScanLog.ENGINE_CREDENTIAL,
            "object_type": EcubeAccessScanLog.TYPE_CREDENTIAL,
            "token": token,
            "normalized_code": f"ECA:CRED:{token}",
        }

    return {
        "engine": EcubeAccessScanLog.ENGINE_PRETIX,
        "object_type": EcubeAccessScanLog.TYPE_TICKET,
        "token": payload,
        "normalized_code": payload,
    }


def _resolve_manual_credential_token(event, payload: str):
    payload = _clean_payload(payload)
    if not payload:
        return None

    if payload.startswith("ECA:CRED:"):
        token = payload.replace("ECA:CRED:", "", 1).strip()
        token = _clean_token(token)
        return token or None

    token = _clean_token(payload)
    if not token:
        return None

    credential = AdmissionCredential.objects.filter(
        event=event,
        qr_token=token,
    ).only("id", "qr_token").first()

    if credential:
        return credential.qr_token

    return None


def _normalize_credential_result(event, credential, validation, action, gate="", operator_name="", device_id="", raw_payload=""):
    result = validation["result"]
    ok = validation["ok"]
    message = validation["message"]

    if credential and ok:
        record_scan_event(
            event=event,
            credential=credential,
            action=action,
            result=result,
            message=message,
            gate=gate or "",
            operator_name=operator_name or "",
            device_id=device_id or "",
            payload_snapshot={"raw_payload": raw_payload},
        )

    response = {
        "ok": ok,
        "result": result,
        "engine": "ecube_access",
        "object_type": "credential",
        "event": {
            "slug": event.slug,
            "name": str(event.name),
        },
        "display_name": getattr(credential, "holder_name", "") if credential else "",
        "display_type": f"{credential.get_credential_type_display()} Credential" if credential else "Credential",
        "code": getattr(credential, "credential_code", ""),
        "photo_url": credential.holder_photo.url if credential and getattr(credential, "holder_photo", None) else None,
        "message": message,
        "gate": gate or "",
        "timestamp": timezone.now().isoformat(),
        "meta": {
            "action": action,
            "entry_mode": credential.entry_mode if credential else "",
            "is_inside": credential.is_inside if credential else False,
        },
    }
    return response


def _error_response(event, payload, message, action, gate=""):
    return {
        "ok": False,
        "result": "error",
        "engine": "ecube_access",
        "object_type": "unknown",
        "event": {
            "slug": event.slug,
            "name": str(event.name),
        },
        "display_name": "",
        "display_type": "Unknown",
        "code": payload,
        "photo_url": None,
        "message": message,
        "gate": gate or "",
        "timestamp": timezone.now().isoformat(),
        "meta": {"action": action},
    }


def _eca_api_base():
    base = (os.getenv("ECUBE_ACCESS_PRETIX_API_BASE") or "").strip().rstrip("/")
    if not base:
        base = "https://pretix.example.invalid"
    return base


def _eca_pretix_headers():
    token = ""
    token_file = "/data/ecube_access_pretix_api_token.txt"
    try:
        if os.path.exists(token_file):
            token = open(token_file, "r", encoding="utf-8").read().strip()
    except Exception:
        token = ""

    if not token:
        token = (os.getenv("ECUBE_ACCESS_PRETIX_API_TOKEN") or "").strip()

    if not token:
        return None

    return {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _eca_parse_list_ids(raw: str):
    out = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


def _eca_localized_name(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("en"):
            return str(value.get("en"))
        for v in value.values():
            if v:
                return str(v)
        return ""
    if value is None:
        return ""
    return str(value)


def _eca_discover_list_ids(event):
    env_ids = _eca_parse_list_ids(os.getenv("ECUBE_ACCESS_PRETIX_LIST_IDS", ""))
    if env_ids:
        return env_ids, None

    headers = _eca_pretix_headers()
    if not headers:
        return None, "Missing ECUBE_ACCESS_PRETIX_API_TOKEN"

    url = f"{_eca_api_base()}/api/v1/organizers/{event.organizer.slug}/events/{event.slug}/checkinlists/"
    try:
        r = requests.get(url, headers=headers, timeout=8)
    except Exception as exc:
        return None, f"Could not load Pretix check-in lists: {exc}"

    if r.status_code != 200:
        return None, f"Pretix check-in list lookup failed ({r.status_code})"

    try:
        data = r.json()
    except Exception:
        return None, "Pretix check-in list lookup returned invalid JSON"

    results = data.get("results") or []
    if len(results) == 1:
        return [results[0]["id"]], None
    if len(results) == 0:
        return None, "No Pretix check-in list exists for this event"
    return None, "Multiple Pretix check-in lists found. Set ECUBE_ACCESS_PRETIX_LIST_IDS to the correct list ID(s)."


def _eca_find_exclusive_access_application(event, position):
    position = position or {}
    order_code = (position.get("order") or "").strip()
    positionid = position.get("positionid")

    qs = ExclusiveAccessApplication.objects.filter(event=event).select_related("approved_order_position")

    if order_code and positionid not in (None, ""):
        app = qs.filter(
            approved_order_code=order_code,
            approved_order_position__positionid=positionid,
        ).first()
        if app:
            return app

    if order_code:
        app = qs.filter(approved_order_code=order_code).first()
        if app:
            return app

    return None


def _eca_pretix_display(position, payload):
    position = position or {}
    attendee = position.get("attendee_name") or position.get("company") or ""
    order = position.get("order")
    posid = position.get("positionid")
    if not attendee:
        if order and posid is not None:
            attendee = f"{order}-{posid}"
        else:
            attendee = "Pretix Ticket"

    item = position.get("item") or {}
    if isinstance(item, dict):
        display_type = _eca_localized_name(item.get("name")) or "Pretix Ticket"
    else:
        display_type = _eca_localized_name(item) or "Pretix Ticket"

    code = payload
    if order and posid is not None:
        code = f"{order}-{posid}"

    return attendee, display_type, code


def _eca_pretix_result_from_response(event, payload, action, gate, data):
    position = data.get("position") or {}
    attendee, display_type, code = _eca_pretix_display(position, payload)
    application = _eca_find_exclusive_access_application(event, position)

    if application and getattr(application, "full_name", ""):
        attendee = application.full_name or attendee

    photo_url = None
    if application and getattr(application, "photo", None):
        try:
            photo_url = application.photo.url
        except Exception:
            photo_url = None

    if data.get("status") == "ok":
        return {
            "ok": True,
            "result": "allowed_exit" if action == "exit" else "allowed",
            "engine": "pretix",
            "object_type": "ticket",
            "event": {"slug": event.slug, "name": str(event.name)},
            "display_name": attendee,
            "display_type": display_type,
            "code": code,
            "photo_url": photo_url,
            "message": "Exit allowed." if action == "exit" else "Entry allowed.",
            "gate": gate or "",
            "timestamp": timezone.now().isoformat(),
            "meta": {
                "action": action,
                "order": position.get("order"),
                "positionid": position.get("positionid"),
                "raw": data,
            },
        }

    if data.get("status") == "incomplete":
        return {
            "ok": False,
            "result": "denied",
            "engine": "pretix",
            "object_type": "ticket",
            "event": {"slug": event.slug, "name": str(event.name)},
            "display_name": attendee,
            "display_type": display_type,
            "code": code,
            "photo_url": photo_url,
            "message": "Pretix requires question handling for this ticket, which Ecube Access does not support yet.",
            "gate": gate or "",
            "timestamp": timezone.now().isoformat(),
            "meta": {"action": action, "raw": data},
        }

    reason = data.get("reason") or "invalid"
    reason_explanation = data.get("reason_explanation") or ""

    result_map = {
        "invalid": "invalid",
        "blocked": "blocked",
        "revoked": "revoked",
        "invalid_time": "expired",
        "already_redeemed": "not_inside" if action == "exit" else "duplicate",
        "unpaid": "denied",
        "product": "denied",
        "rules": "denied",
        "ambiguous": "denied",
        "unapproved": "denied",
        "canceled": "denied",
    }

    message_map = {
        "invalid": "Ticket not recognized.",
        "blocked": "Ticket is blocked.",
        "revoked": "Ticket has been revoked.",
        "invalid_time": "Ticket is not valid at this time.",
        "already_redeemed": "Ticket is not currently inside." if action == "exit" else "Ticket already redeemed.",
        "unpaid": "Ticket order is not paid.",
        "product": "Ticket is not valid for this check-in list.",
        "rules": "Pretix rules denied this scan.",
        "ambiguous": "Multiple tickets matched this scan.",
        "unapproved": "Order is not approved.",
        "canceled": "Ticket is canceled.",
    }

    return {
        "ok": False,
        "result": result_map.get(reason, "error"),
        "engine": "pretix",
        "object_type": "ticket",
        "event": {"slug": event.slug, "name": str(event.name)},
        "display_name": attendee,
        "display_type": display_type,
        "code": code,
        "photo_url": photo_url,
        "message": reason_explanation or message_map.get(reason, f"Pretix validation failed: {reason}"),
        "gate": gate or "",
        "timestamp": timezone.now().isoformat(),
        "meta": {"action": action, "reason": reason, "raw": data},
    }


def _pretix_ticket_placeholder_response(event, payload, action="entry", gate="", operator_name="", device_id=""):
    headers = _eca_pretix_headers()
    if not headers:
        return _error_response(
            event,
            payload,
            "Pretix native ticket scanning is not configured: missing ECUBE_ACCESS_PRETIX_API_TOKEN",
            action=action,
            gate=gate,
        )

    list_ids, err = _eca_discover_list_ids(event)
    if err:
        return _error_response(event, payload, err, action=action, gate=gate)

    url = f"{_eca_api_base()}/api/v1/organizers/{event.organizer.slug}/checkinrpc/redeem/"
    body = {
        "secret": payload,
        "source_type": "barcode",
        "lists": list_ids,
        "type": "exit" if action == "exit" else "entry",
        "force": False,
        "questions_supported": False,
        "ignore_unpaid": False,
    }

    try:
        r = requests.post(
            url,
            headers=headers,
            json=body,
            params=[("expand", "item"), ("expand", "subevent")],
            timeout=10,
        )
    except Exception as exc:
        return _error_response(event, payload, f"Pretix redeem request failed: {exc}", action=action, gate=gate)

    try:
        data = r.json()
    except Exception:
        return _error_response(event, payload, f"Pretix redeem returned invalid JSON ({r.status_code})", action=action, gate=gate)

    return _eca_pretix_result_from_response(event, payload, action, gate, data)


def write_scan_log(*, event, classified, payload, action, response, gate="", operator_name="", device_id=""):
    return EcubeAccessScanLog.objects.create(
        event=event,
        engine=classified.get("engine") or EcubeAccessScanLog.ENGINE_UNKNOWN,
        object_type=classified.get("object_type") or EcubeAccessScanLog.TYPE_UNKNOWN,
        action=action,
        raw_payload=payload,
        normalized_code=classified.get("normalized_code") or payload,
        display_name=response.get("display_name") or "",
        display_type=response.get("display_type") or "",
        result=response.get("result") or EcubeAccessScanLog.RESULT_PENDING,
        message=response.get("message") or "",
        gate=gate or "",
        operator_name=operator_name or "",
        device_id=device_id or "",
        response_snapshot=response,
    )


def process_scan(*, event, payload, action="entry", gate="", operator_name="", device_id=""):
    raw_payload = (payload or "").strip()
    action = (action or "entry").strip().lower()
    if action not in {"entry", "exit"}:
        action = "entry"

    try:
        classified = classify_payload(raw_payload)

        if classified["engine"] == EcubeAccessScanLog.ENGINE_CREDENTIAL:
            token = classified.get("token") or ""
            if not token:
                response = _error_response(event, raw_payload, "Credential token missing", action=action, gate=gate)
            else:
                validation = validate_credential_token(event=event, token=token, action=action)
                credential = validation.get("credential")
                response = _normalize_credential_result(
                    event,
                    credential,
                    validation,
                    action=action,
                    gate=gate,
                    operator_name=operator_name,
                    device_id=device_id,
                    raw_payload=raw_payload,
                )
        else:
            manual_token = _resolve_manual_credential_token(event, raw_payload)
            if manual_token:
                classified = {
                    "engine": EcubeAccessScanLog.ENGINE_CREDENTIAL,
                    "object_type": EcubeAccessScanLog.TYPE_CREDENTIAL,
                    "token": manual_token,
                    "normalized_code": f"ECA:CRED:{manual_token}",
                }
                validation = validate_credential_token(event=event, token=manual_token, action=action)
                credential = validation.get("credential")
                response = _normalize_credential_result(
                    event,
                    credential,
                    validation,
                    action=action,
                    gate=gate,
                    operator_name=operator_name,
                    device_id=device_id,
                    raw_payload=raw_payload,
                )
            else:
                response = _pretix_ticket_placeholder_response(
                    event,
                    raw_payload,
                    action=action,
                    gate=gate,
                    operator_name=operator_name,
                    device_id=device_id,
                )

    except Exception as exc:
        classified = {
            "engine": EcubeAccessScanLog.ENGINE_UNKNOWN,
            "object_type": EcubeAccessScanLog.TYPE_UNKNOWN,
            "normalized_code": raw_payload,
        }
        response = _error_response(event, raw_payload, f"Scan processing error: {exc}", action=action, gate=gate)

    write_scan_log(
        event=event,
        classified=classified,
        payload=raw_payload,
        action=action,
        response=response,
        gate=gate,
        operator_name=operator_name,
        device_id=device_id,
    )

    return response
