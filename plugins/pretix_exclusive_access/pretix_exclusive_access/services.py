import logging
import secrets
import string

from django.template.loader import render_to_string
from django.utils import timezone
from pretix.base.i18n import LazyI18nString
from pretix.base.services.mail import mail
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger(__name__)

from .models import ApplicationStatus


def generate_access_token(length=40):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_access_link(application):
    return build_absolute_uri(
        application.event,
        "plugins:pretix_exclusive_access:approved_access",
        kwargs={
            "token": application.access_token,
        },
    )


def send_notification(application, channel="email"):
    """Dispatch notification based on application status.
    Currently only email is implemented. SMS/WhatsApp channels will be
    added when the pretix_messaging plugin is ready."""
    if channel != "email":
        logger.warning("Channel '%s' not yet implemented, falling back to email", channel)

    if application.status == "approved":
        send_approval_email(application)
    elif application.status == "rejected":
        send_rejection_email(application)
    else:
        logger.warning("Cannot send notification for application %s with status '%s'", application.pk, application.status)


def send_approval_email(application):
    event = application.event
    body_text = render_to_string(
        "pretix_exclusive_access/emails/approval.txt",
        {
            "application": application,
            "event": event,
            "access_link": build_access_link(application),
        },
    )
    subject = (
        event.settings.get(
            "exclusive_access_approval_email_subject",
            default="You're in - your access request has been approved",
        ) or "You're in - your access request has been approved"
    )
    mail(
        email=application.email,
        subject=subject,
        template=LazyI18nString(body_text),
        context={},
        event=event,
        locale=event.settings.locale or "en",
    )
    logger.info("Sent approval email for application %s to %s", application.pk, application.email)


def send_rejection_email(application):
    event = application.event
    body_text = render_to_string(
        "pretix_exclusive_access/emails/rejection.txt",
        {
            "application": application,
            "event": event,
        },
    )
    subject = (
        event.settings.get(
            "exclusive_access_rejection_email_subject",
            default="Update on your access request",
        ) or "Update on your access request"
    )
    mail(
        email=application.email,
        subject=subject,
        template=LazyI18nString(body_text),
        context={},
        event=event,
        locale=event.settings.locale or "en",
    )
    logger.info("Sent rejection email for application %s to %s", application.pk, application.email)
