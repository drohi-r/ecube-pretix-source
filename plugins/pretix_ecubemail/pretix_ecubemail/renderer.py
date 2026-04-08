import logging
from itertools import groupby

import bleach

logger = logging.getLogger(__name__)
import css_inline
from django.conf import settings
from django.db.models import Count
from django.template.loader import get_template
from django.utils.translation import get_language, gettext_lazy as _
from pretix.base.email import (
    DEFAULT_CALLBACKS,
    EMAIL_RE,
    URL_RE,
    BaseHTMLMailRenderer,
    FormattedString,
    SafeFormatter,
    abslink_callback,
    format_map,
    markdown_compile_email,
    truelink_callback,
)

from pretix_event_themes.services.resolver import resolve_absolute_design_profile


class EcubeMailRenderer(BaseHTMLMailRenderer):
    verbose_name = _("Ecube branded")
    identifier = "ecube_shell"
    thumbnail_filename = "pretix_ecubemail/mail-thumb.svg"

    def compile_markdown(self, plaintext, context=None):
        return markdown_compile_email(plaintext, context=context)

    def render(self, plain_body: str, plain_signature: str, subject: str, order=None,
               position=None, context=None) -> str:
        apply_format_map = not isinstance(plain_body, FormattedString)
        body_md = self.compile_markdown(plain_body, context=context)
        if context:
            linker = bleach.Linker(
                url_re=URL_RE,
                email_re=EMAIL_RE,
                callbacks=DEFAULT_CALLBACKS + [truelink_callback, abslink_callback],
                parse_email=True,
            )
            if apply_format_map:
                body_md = format_map(
                    body_md,
                    context=context,
                    mode=SafeFormatter.MODE_RICH_TO_HTML,
                    linkifier=linker,
                )

        profile = resolve_absolute_design_profile(self.event)
        hero_banner_url = profile.hero_email_banner_url if profile.use_hero_in_email else ""
        logo_url = profile.logo_email_url or profile.logo_url
        event_object = position.subevent if position and getattr(position, "subevent_id", None) else self.event
        action_url = self._context_value(context, "url")
        payment_info_raw = self._context_value(context, "payment_info")
        payment_info = str(payment_info_raw).strip() if payment_info_raw else ""
        recipient_name = self._context_value(context, "name")
        htmlctx = {
            "site": settings.PRETIX_INSTANCE_NAME,
            "site_url": settings.SITE_URL,
            "subject": str(subject),
            "body": body_md,
            "rtl": get_language() in settings.LANGUAGES_RTL or get_language().split("-")[0] in settings.LANGUAGES_RTL,
            "event": self.event,
            "organizer": self.organizer or getattr(self.event, "organizer", None),
            "profile": profile,
            "hero_banner_url": hero_banner_url,
            "logo_url": logo_url,
            "signature": "",
            "order": order,
            "position": position,
            "event_object": event_object,
            "status_label": self._status_label(order),
            "summary_total": self._format_total(order),
            "status_icon": self._status_icon(order),
            "status_color": self._status_color(order),
            "status_summary": self._status_summary(order, event_object, recipient_name),
            "action_url": action_url,
            "action_label": self._action_label(order),
            "payment_info": payment_info,
            "recipient_name": recipient_name,
        }

        if plain_signature:
            signature_md = self.compile_markdown(plain_signature.replace("\n", "<br>\n"))
            htmlctx["signature"] = signature_md

        if order:
            positions = list(order.positions.select_related(
                "item", "variation", "subevent", "addon_to"
            ).annotate(
                has_addons=Count("addons")
            ))
            htmlctx["cart"] = [(k, list(v)) for k, v in groupby(
                sorted(
                    positions,
                    key=lambda op: (
                        (op.addon_to.positionid if op.addon_to_id else op.positionid),
                        op.positionid,
                    )
                ),
                key=lambda op: (
                    op.item,
                    op.variation,
                    op.subevent,
                    op.attendee_name,
                    op.addon_to_id,
                    (op.pk if op.has_addons else None),
                )
            )]

        tpl = get_template("pretix_ecubemail/html_mail.html")
        body_html = tpl.render(htmlctx)
        return css_inline.CSSInliner(keep_style_tags=False).inline(body_html)

    def _status_label(self, order):
        if not order:
            return _("Event update")
        if getattr(order, "status", "") == "p":
            return _("Payment confirmed")
        if getattr(order, "status", "") == "n":
            return _("Pending payment")
        if getattr(order, "status", "") == "c":
            return _("Order canceled")
        return _("Order update")

    def _status_icon(self, order):
        if not order:
            return "•"
        if getattr(order, "status", "") == "p":
            return "✓"
        if getattr(order, "status", "") == "n":
            return "⏳"
        if getattr(order, "status", "") == "c":
            return "×"
        return "•"

    def _status_color(self, order):
        if not order:
            return "#E83845"
        if getattr(order, "status", "") == "p":
            return "#E83845"
        if getattr(order, "status", "") == "n":
            return "#E8B931"
        if getattr(order, "status", "") == "c":
            return "#E83845"
        return "#40E0D0"

    def _status_summary(self, order, event_object, recipient_name):
        event_name = getattr(event_object, "name", "") or getattr(self.event, "name", "")
        if order and getattr(order, "status", "") == "p":
            if recipient_name:
                return _("You're in, {name}.").format(name=recipient_name)
            return _("You're in.")
        if order and getattr(order, "status", "") == "n":
            return _("Your spot for {event} is reserved.").format(event=event_name)
        if order and getattr(order, "status", "") == "c":
            return _("Your order for {event} has been canceled.").format(event=event_name)
        return event_name

    def _action_label(self, order):
        if not order:
            return _("View details")
        if getattr(order, "status", "") == "p":
            return _("View order & download tickets")
        if getattr(order, "status", "") == "n":
            return _("Complete payment")
        if getattr(order, "status", "") == "c":
            return _("View order details")
        return _("Open order")

    def _format_total(self, order):
        if not order:
            return ""
        try:
            from babel.numbers import format_currency
            currency = getattr(order.event, "currency", "USD") or "USD"
            return format_currency(order.total, currency, locale="en_US")
        except Exception:
            logger.debug("Currency formatting failed for order %s", getattr(order, "code", "?"))
            return str(getattr(order, "total", ""))

    def _context_value(self, context, key):
        if not context:
            return ""
        if isinstance(context, dict):
            return context.get(key, "") or ""
        return getattr(context, key, "") or ""
