import csv
import io
import logging
import secrets

from django.db import transaction

logger = logging.getLogger(__name__)
from django.utils import timezone


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _set_review_metadata(application, reviewed_by=None, guest_category=None, status_reason=None, internal_note=None):
    application.reviewed_at = timezone.now()

    if reviewed_by is not None:
        application.reviewed_by = reviewed_by

    if guest_category is not None and hasattr(application, "guest_category"):
        application.guest_category = guest_category

    if status_reason is not None and hasattr(application, "status_reason"):
        application.status_reason = _clean_text(status_reason)

    if internal_note is not None and hasattr(application, "internal_note"):
        application.internal_note = _clean_text(internal_note)


def _ensure_access_token(application):
    if getattr(application, "access_token", None):
        return application.access_token

    application.access_token = secrets.token_urlsafe(32)
    application.access_token_created_at = timezone.now()
    return application.access_token


@transaction.atomic
def approve_application_v11(
    application,
    reviewed_by=None,
    guest_category=None,
    status_reason=None,
    internal_note=None,
    send_email=False,
):
    application.status = "approved"
    _set_review_metadata(
        application,
        reviewed_by=reviewed_by,
        guest_category=guest_category,
        status_reason=status_reason,
        internal_note=internal_note,
    )
    _ensure_access_token(application)
    application.save()

    if send_email:
        try:
            from .services import send_approval_email
            send_approval_email(application)
        except Exception:
            logger.exception("Failed to send approval email for application %s", application.pk)

    return application


@transaction.atomic
def reject_application_v11(
    application,
    reviewed_by=None,
    status_reason=None,
    internal_note=None,
    send_email=False,
):
    application.status = "rejected"
    _set_review_metadata(
        application,
        reviewed_by=reviewed_by,
        status_reason=status_reason,
        internal_note=internal_note,
    )
    application.save()

    if send_email:
        try:
            from .services import send_rejection_email
            send_rejection_email(application)
        except Exception:
            logger.exception("Failed to send rejection email for application %s", application.pk)

    return application


@transaction.atomic
def bulk_approve_applications_v11(
    queryset,
    reviewed_by=None,
    guest_category=None,
    status_reason=None,
    internal_note=None,
    send_email=False,
):
    results = {
        "processed": 0,
        "approved": 0,
        "skipped": 0,
        "skipped_ids": [],
    }

    for application in queryset.select_for_update():
        results["processed"] += 1

        if application.status == "approved":
            results["skipped"] += 1
            results["skipped_ids"].append(application.pk)
            continue

        approve_application_v11(
            application,
            reviewed_by=reviewed_by,
            guest_category=guest_category,
            status_reason=status_reason,
            internal_note=internal_note,
            send_email=send_email,
        )
        results["approved"] += 1

    return results


@transaction.atomic
def bulk_reject_applications_v11(
    queryset,
    reviewed_by=None,
    status_reason=None,
    internal_note=None,
):
    results = {
        "processed": 0,
        "rejected": 0,
        "skipped": 0,
        "skipped_ids": [],
    }

    for application in queryset.select_for_update():
        results["processed"] += 1

        if application.status == "rejected":
            results["skipped"] += 1
            results["skipped_ids"].append(application.pk)
            continue

        reject_application_v11(
            application,
            reviewed_by=reviewed_by,
            status_reason=status_reason,
            internal_note=internal_note,
        )
        results["rejected"] += 1

    return results


def export_applications_csv_v11(queryset):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "application_id",
        "submitted_at",
        "reviewed_at",
        "status",
        "status_reason",
        "guest_category",
        "source",
        "name",
        "email",
        "phone",
        "instagram_social",
        "gender",
        "referred_by",
        "requested_item",
        "applicant_notes",
        "internal_note",
        "has_photo",
        "access_token_present",
        "approved_order_code",
        "approved_order_position",
        "reviewed_by",
    ])

    for app in queryset:
        requested_item = ""
        item_obj = getattr(app, "requested_item", None) or getattr(app, "item", None)
        if item_obj:
            try:
                requested_item = str(item_obj)
            except Exception:
                logger.debug("Could not stringify item object, using name fallback")
                requested_item = getattr(item_obj, "name", "")

        reviewed_by = ""
        if getattr(app, "reviewed_by", None):
            reviewed_by = (
                getattr(app.reviewed_by, "username", "")
                or getattr(app.reviewed_by, "email", "")
                or str(app.reviewed_by)
            )

        writer.writerow([
            app.pk,
            getattr(app, "submitted_at", "") or getattr(app, "created_at", "") or "",
            getattr(app, "reviewed_at", "") or "",
            getattr(app, "status", "") or "",
            getattr(app, "status_reason", "") or "",
            getattr(app, "guest_category", "") or "",
            getattr(app, "source", "") or "",
            getattr(app, "full_name", "") or getattr(app, "name", "") or "",
            getattr(app, "email", "") or "",
            getattr(app, "phone", "") or "",
            getattr(app, "instagram_handle", "") or getattr(app, "instagram", "") or "",
            getattr(app, "gender", "") or "",
            getattr(app, "referred_by", "") or "",
            requested_item,
            getattr(app, "notes", "") or "",
            getattr(app, "internal_note", "") or "",
            bool(getattr(app, "photo", None)),
            bool(getattr(app, "access_token", "")),
            getattr(app, "approved_order_code", "") or "",
            getattr(app, "approved_order_position", "") or "",
            reviewed_by,
        ])

    return output.getvalue()
