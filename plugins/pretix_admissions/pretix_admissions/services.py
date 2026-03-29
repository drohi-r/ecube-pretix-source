import logging
import secrets

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

from .models import AdmissionCredential, AdmissionScanEvent


def default_entry_mode_for_type(credential_type):
    if credential_type in {
        AdmissionCredential.TYPE_ARTIST,
        AdmissionCredential.TYPE_STAFF,
        AdmissionCredential.TYPE_MEDIA,
        AdmissionCredential.TYPE_VENDOR,
    }:
        return AdmissionCredential.ENTRY_MODE_REENTRY_AFTER_EXIT
    return AdmissionCredential.ENTRY_MODE_SINGLE


def generate_credential_code(event):
    prefix = f"ADM-{event.slug.upper()[:8]}"
    last = (
        AdmissionCredential.objects.filter(event=event)
        .order_by("-id")
        .values_list("id", flat=True)
        .first()
        or 0
    )
    return f"{prefix}-{last + 1:06d}"


def generate_qr_token():
    return secrets.token_urlsafe(32)


@transaction.atomic
def issue_credential(
    *,
    event,
    holder_name,
    holder_email="",
    holder_phone="",
    credential_type=AdmissionCredential.TYPE_GUEST,
    entry_mode="",
    label="",
    notes="",
    valid_from=None,
    valid_until=None,
    holder_photo=None,
    issued_by=None,
):
    effective_entry_mode = entry_mode or default_entry_mode_for_type(credential_type)

    credential = AdmissionCredential.objects.create(
        event=event,
        credential_code=generate_credential_code(event),
        qr_token=generate_qr_token(),
        credential_type=credential_type,
        status=AdmissionCredential.STATUS_ACTIVE,
        entry_mode=effective_entry_mode,
        holder_name=holder_name,
        holder_email=holder_email or "",
        holder_phone=holder_phone or "",
        holder_photo=holder_photo,
        label=label or "",
        notes=notes or "",
        valid_from=valid_from,
        valid_until=valid_until,
        issued_at=timezone.now(),
        issued_by=issued_by,
    )
    return credential


def validate_credential_token(*, event, token, action=AdmissionScanEvent.ACTION_ENTRY):
    now = timezone.now()
    action = (action or AdmissionScanEvent.ACTION_ENTRY).strip()

    try:
        credential = AdmissionCredential.objects.get(event=event, qr_token=token)
    except AdmissionCredential.DoesNotExist:
        return {
            "ok": False,
            "result": AdmissionScanEvent.RESULT_INVALID,
            "message": "Credential not found",
            "credential": None,
        }

    if credential.status == AdmissionCredential.STATUS_REVOKED:
        return {
            "ok": False,
            "result": AdmissionScanEvent.RESULT_REVOKED,
            "message": "Credential revoked",
            "credential": credential,
        }

    if credential.status == AdmissionCredential.STATUS_BLOCKED:
        return {
            "ok": False,
            "result": AdmissionScanEvent.RESULT_BLOCKED,
            "message": "Credential blocked",
            "credential": credential,
        }

    if credential.status == AdmissionCredential.STATUS_EXPIRED:
        return {
            "ok": False,
            "result": AdmissionScanEvent.RESULT_EXPIRED,
            "message": "Credential expired",
            "credential": credential,
        }

    if credential.valid_from and now < credential.valid_from:
        return {
            "ok": False,
            "result": AdmissionScanEvent.RESULT_DENIED,
            "message": "Credential not yet valid",
            "credential": credential,
        }

    if credential.valid_until and now > credential.valid_until:
        return {
            "ok": False,
            "result": AdmissionScanEvent.RESULT_EXPIRED,
            "message": "Credential validity window ended",
            "credential": credential,
        }

    if action == AdmissionScanEvent.ACTION_EXIT:
        if credential.is_inside:
            return {
                "ok": True,
                "result": AdmissionScanEvent.RESULT_ALLOWED_EXIT,
                "message": "Exit recorded",
                "credential": credential,
            }
        return {
            "ok": False,
            "result": AdmissionScanEvent.RESULT_NOT_INSIDE,
            "message": "Credential is not currently marked inside",
            "credential": credential,
        }

    # Entry logic
    if credential.entry_mode == AdmissionCredential.ENTRY_MODE_SINGLE:
        if credential.scan_count > 0 or credential.status == AdmissionCredential.STATUS_USED:
            return {
                "ok": False,
                "result": AdmissionScanEvent.RESULT_DUPLICATE,
                "message": "Single-entry credential already used",
                "credential": credential,
            }
        return {
            "ok": True,
            "result": AdmissionScanEvent.RESULT_ALLOWED,
            "message": "Entry allowed",
            "credential": credential,
        }

    if credential.entry_mode == AdmissionCredential.ENTRY_MODE_REENTRY_AFTER_EXIT:
        if credential.is_inside:
            return {
                "ok": False,
                "result": AdmissionScanEvent.RESULT_DUPLICATE,
                "message": "Credential already inside. Exit scan required before re-entry.",
                "credential": credential,
            }
        return {
            "ok": True,
            "result": AdmissionScanEvent.RESULT_ALLOWED,
            "message": "Entry allowed",
            "credential": credential,
        }

    if credential.entry_mode == AdmissionCredential.ENTRY_MODE_MULTI:
        return {
            "ok": True,
            "result": AdmissionScanEvent.RESULT_ALLOWED,
            "message": "Entry allowed",
            "credential": credential,
        }

    return {
        "ok": False,
        "result": AdmissionScanEvent.RESULT_ERROR,
        "message": "Unknown entry policy",
        "credential": credential,
    }


@transaction.atomic
def record_scan_event(
    *,
    event,
    credential,
    action=AdmissionScanEvent.ACTION_ENTRY,
    result,
    message="",
    gate="",
    operator_name="",
    device_id="",
    payload_snapshot=None,
):
    scan = AdmissionScanEvent.objects.create(
        event=event,
        credential=credential,
        action=action,
        result=result,
        message=message or "",
        gate=gate or "",
        operator_name=operator_name or "",
        device_id=device_id or "",
        payload_snapshot=payload_snapshot,
    )

    update_fields = ["last_scanned_at", "last_scanned_gate", "updated_at"]
    credential.last_scanned_at = scan.scanned_at
    credential.last_scanned_gate = gate or ""

    if action == AdmissionScanEvent.ACTION_ENTRY and result == AdmissionScanEvent.RESULT_ALLOWED:
        credential.scan_count += 1
        credential.is_inside = True
        credential.last_entry_at = scan.scanned_at
        update_fields.extend(["scan_count", "is_inside", "last_entry_at"])

        if credential.entry_mode == AdmissionCredential.ENTRY_MODE_SINGLE:
            credential.status = AdmissionCredential.STATUS_USED
            update_fields.append("status")

    if action == AdmissionScanEvent.ACTION_EXIT and result == AdmissionScanEvent.RESULT_ALLOWED_EXIT:
        credential.is_inside = False
        credential.last_exit_at = scan.scanned_at
        update_fields.extend(["is_inside", "last_exit_at"])

    credential.save(update_fields=update_fields)
    return scan


@transaction.atomic
def mark_credential_revoked(*, credential, user=None, reason=""):
    credential.status = AdmissionCredential.STATUS_REVOKED
    credential.revoked_at = timezone.now()
    credential.revoked_by = user
    credential.revocation_reason = reason or ""
    credential.save(
        update_fields=[
            "status",
            "revoked_at",
            "revoked_by",
            "revocation_reason",
            "updated_at",
        ]
    )
    return credential


@transaction.atomic
def mark_credential_blocked(*, credential):
    credential.status = AdmissionCredential.STATUS_BLOCKED
    credential.save(update_fields=["status", "updated_at"])
    return credential


@transaction.atomic
def reactivate_credential(*, credential):
    credential.status = AdmissionCredential.STATUS_ACTIVE
    credential.save(update_fields=["status", "updated_at"])
    return credential

