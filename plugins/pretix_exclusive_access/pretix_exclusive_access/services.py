import secrets
import string

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ApplicationStatus


def generate_access_token(length=40):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_access_link(application):
    return f"https://tickets.ecube-entertainment.com/{application.event.organizer.slug}/{application.event.slug}/access/{application.access_token}/"


def approve_application(application, reviewer):
    if application.status == ApplicationStatus.APPROVED and application.access_token:
        return application

    event = application.event

    application.status = ApplicationStatus.APPROVED
    application.voucher_code = ""
    application.voucher_id = None
    application.access_token = generate_access_token()
    application.access_token_created_at = timezone.now()
    application.identity_photo_locked = True
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save()

    body = render_to_string(
        "pretix_exclusive_access/emails/approval.txt",
        {
            "application": application,
            "event": event,
            "access_link": build_access_link(application),
        },
    )
    send_mail(
        event.settings.get(
            "exclusive_access_approval_email_subject",
            default="Your access request has been approved",
        ) or "Your access request has been approved",
        body,
        None,
        [application.email],
    )
    return application


def reject_application(application, reviewer):
    if application.status == ApplicationStatus.REJECTED:
        return application

    application.status = ApplicationStatus.REJECTED
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save()

    body = render_to_string(
        "pretix_exclusive_access/emails/rejection.txt",
        {
            "application": application,
            "event": application.event,
        },
    )
    send_mail(
        application.event.settings.get(
            "exclusive_access_rejection_email_subject",
            default="Update on your access request",
        ) or "Update on your access request",
        body,
        None,
        [application.email],
    )
    return application

