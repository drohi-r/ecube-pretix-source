import logging
from io import BytesIO
from pathlib import Path

from babel.numbers import format_currency

logger = logging.getLogger(__name__)
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from reportlab.graphics import renderPDF, shapes
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from pretix.base.ticketoutput import BaseTicketOutput
from pretix_event_themes.services.resolver import resolve_design_profile
from pretix_event_themes.theme_config import MEDIA_ROOT, MEDIA_URL


PAGE_SIZE = landscape((99 * mm, 210 * mm))
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
TICKET = {
    "left_panel_width": 56 * mm,
    "right_panel_width": 40 * mm,
    "content_padding": 9 * mm,
    "outer_margin": 4 * mm,
    "top_stripe_height": 2.8 * mm,
    "bottom_stripe_height": 1.4 * mm,
    "qr_size": 28 * mm,
    "panel_inset": 7 * mm,
    "panel_top": 8 * mm,
    "panel_bottom": 8 * mm,
}
FONT_FILES = {
    "ticket_display": "BebasNeue-Regular.ttf",
    "ticket_mono": "ShareTechMono-400.ttf",
    "ticket_body": "Outfit-400.ttf",
    "ticket_body_medium": "Outfit-500.ttf",
    "ticket_body_semibold": "Outfit-600.ttf",
}
FONT_ROLES = {
    "display": ("ticket_display", "Helvetica-Bold"),
    "mono": ("ticket_mono", "Courier"),
    "body": ("ticket_body", "Helvetica"),
    "body_medium": ("ticket_body_medium", "Helvetica-Bold"),
    "body_semibold": ("ticket_body_semibold", "Helvetica-Bold"),
}
_FONTS_READY = False


class EcubeTicketOutput(BaseTicketOutput):
    identifier = "ecube_pdf"
    verbose_name = _("PDF output")
    download_button_text = _("PDF")
    multi_download_button_text = _("Download tickets (PDF)")
    long_download_button_text = _("Download ticket (PDF)")

    def generate(self, position):
        _ensure_brand_fonts()
        buffer = BytesIO()
        profile = resolve_design_profile(self.event)
        pdf = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
        self._draw_ticket(pdf, position, profile)
        pdf.save()
        return "order%s%s.pdf" % (self.event.slug, position.order.code), "application/pdf", buffer.getvalue()

    def generate_order(self, order):
        from pypdf import PdfWriter
        _ensure_brand_fonts()
        profile = resolve_design_profile(self.event)
        merger = PdfWriter()
        for pos in self.get_tickets_to_print(order):
            buf = BytesIO()
            pdf = canvas.Canvas(buf, pagesize=PAGE_SIZE)
            self._draw_ticket(pdf, pos, profile)
            pdf.save()
            buf.seek(0)
            merger.append(buf)
        outbuffer = BytesIO()
        merger.write(outbuffer)
        merger.close()
        outbuffer.seek(0)
        return "order%s%s.pdf" % (self.event.slug, order.code), "application/pdf", outbuffer.read()

    def _draw_ticket(self, pdf, position, profile):
        order = position.order
        event_object = position.subevent or order.event
        access_variant = _resolve_access_variant(position)
        scan_payload = _get_scan_payload(position)
        family = _ticket_palette(profile, access_variant)

        _draw_background(pdf, family)
        _draw_background_image(pdf, _resolve_ticket_background(position, profile))
        _draw_laminate_overlay(pdf, family)
        _draw_grid(pdf)
        _draw_stripes(pdf, family, access_variant)
        _draw_brand_panel(pdf, position, profile, family, access_variant)
        _draw_detail_panel(pdf, position, event_object, profile, family, access_variant)
        _draw_perforation(pdf, family)
        _draw_corner_marks(pdf, family)
        _draw_qr_panel(pdf, profile, family, scan_payload)


def _draw_background(pdf, family):
    pdf.saveState()
    pdf.setFillColor(family["body_bg"])
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    pdf.restoreState()


def _draw_grid(pdf):
    pdf.saveState()
    pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=0.015))
    pdf.setLineWidth(0.25)
    step = 20
    x = 0
    while x <= PAGE_WIDTH:
        pdf.line(x, 0, x, PAGE_HEIGHT)
        x += step
    y = 0
    while y <= PAGE_HEIGHT:
        pdf.line(0, y, PAGE_WIDTH, y)
        y += step
    pdf.restoreState()


def _draw_background_image(pdf, image_reader):
    if not image_reader:
        return
    pdf.saveState()
    try:
        pdf.drawImage(image_reader, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT, preserveAspectRatio=False, mask="auto")
    finally:
        pdf.restoreState()


def _draw_laminate_overlay(pdf, family):
    pdf.saveState()
    pdf.setFillColor(family["laminate"])
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    pdf.restoreState()


def _draw_stripes(pdf, family, access_variant):
    pdf.saveState()
    accent = family["accent"]
    highlight = _lighten(accent, 0.30)
    steps = 80
    stripe_h = TICKET["top_stripe_height"]
    step_w = PAGE_WIDTH / steps
    for i in range(steps):
        t = i / max(steps - 1, 1)
        frac = 1.0 - abs(t * 2 - 1)
        pdf.setFillColor(_blend(accent, highlight, frac))
        pdf.rect(i * step_w, PAGE_HEIGHT - stripe_h, step_w + 0.5, stripe_h, stroke=0, fill=1)
    pdf.setFillColor(family["accent_soft"])
    pdf.rect(0, 0, PAGE_WIDTH, TICKET["bottom_stripe_height"], stroke=0, fill=1)
    pdf.restoreState()


def _draw_brand_panel(pdf, position, profile, family, access_variant):
    logo_reader = _resolve_logo(position, profile)
    panel_left = 8 * mm
    panel_top = PAGE_HEIGHT - (10.4 * mm)
    price_y = 50 * mm
    product_name = _position_product_name(position)
    display_price = _format_price(position)
    pdf.saveState()
    pdf.setFillColor(family["panel_bg"])
    pdf.roundRect(7 * mm, 8 * mm, TICKET["left_panel_width"] - 14 * mm, PAGE_HEIGHT - 16 * mm, 1.5 * mm, stroke=0, fill=1)
    pdf.setStrokeColor(family["panel_border"])
    pdf.roundRect(7 * mm, 8 * mm, TICKET["left_panel_width"] - 14 * mm, PAGE_HEIGHT - 16 * mm, 1.5 * mm, stroke=1, fill=0)
    pdf.setFillColor(family["accent"])
    pdf.rect(7 * mm, PAGE_HEIGHT - 13 * mm, TICKET["left_panel_width"] - 14 * mm, 1.8 * mm, stroke=0, fill=1)

    if logo_reader:
        pdf.drawImage(
            logo_reader,
            panel_left,
            PAGE_HEIGHT - 32 * mm,
            width=TICKET["left_panel_width"] - 16 * mm,
            height=16 * mm,
            preserveAspectRatio=True,
            anchor="nw",
            mask="auto",
        )
        panel_top = PAGE_HEIGHT - (38 * mm)

    _set_font(pdf, "display", 18)
    ecube_w = pdf.stringWidth("ECUBE", _font_name("display"), 18)
    pdf.setFillColor(family["headline"])
    pdf.drawString(panel_left, panel_top, "ECUBE")

    badge_x = panel_left + ecube_w + 2 * mm
    badge_y = panel_top + 0.3 * mm
    badge_width = 13.2 * mm
    badge_height = 4.6 * mm
    pdf.setFillColor(colors.Color(family["accent"].red, family["accent"].green, family["accent"].blue, alpha=0.16))
    pdf.roundRect(badge_x, badge_y, badge_width, badge_height, 1.1 * mm, stroke=0, fill=1)
    pdf.setStrokeColor(colors.Color(family["accent"].red, family["accent"].green, family["accent"].blue, alpha=0.45))
    pdf.roundRect(badge_x, badge_y, badge_width, badge_height, 1.1 * mm, stroke=1, fill=0)
    _set_font(pdf, "mono", 6.2)
    pdf.setFillColor(family["accent"])
    pdf.drawString(badge_x + 1.4 * mm, badge_y + 1.4 * mm, "ACCESS")

    _set_font(pdf, "mono", 6.2)
    pdf.setFillColor(family["muted"])
    pdf.drawString(panel_left, panel_top - 5.1 * mm, "OFFICIAL ENTRY PASS")

    _set_font(pdf, "mono", 6)
    pdf.setFillColor(family["muted"])
    pdf.drawString(panel_left, price_y + 18 * mm, "ORDER")
    _set_font(pdf, "display", 13)
    pdf.setFillColor(family["headline"])
    pdf.drawString(panel_left, price_y + 12 * mm, _text(position.order.code))

    _set_font(pdf, "mono", 6)
    pdf.setFillColor(family["muted"])
    pdf.drawString(panel_left, price_y + 5 * mm, "PRICE")
    _set_font(pdf, "display", 18)
    pdf.setFillColor(family["accent"])
    pdf.drawString(panel_left, price_y - 1 * mm, display_price)

    _set_font(pdf, "mono", 6)
    pdf.setFillColor(family["muted"])
    pdf.drawString(panel_left, price_y - 8 * mm, "TYPE")
    _set_font(pdf, "display", 12.5)
    pdf.setFillColor(family["headline"])
    for idx, line in enumerate(_split_lines(product_name, _font_name("display"), 12.5, TICKET["left_panel_width"] - 20 * mm, 2)):
        pdf.drawString(panel_left, price_y - 13.5 * mm - (idx * 4.7 * mm), line)

    pdf.saveState()
    pdf.translate(TICKET["left_panel_width"] - 5 * mm, PAGE_HEIGHT / 2)
    pdf.rotate(90)
    _set_font(pdf, "display", 22)
    pdf.setFillColor(family["watermark"])
    pdf.drawString(0, 0, "ADMIT ONE")
    pdf.restoreState()
    pdf.restoreState()


def _draw_detail_panel(pdf, position, event_object, profile, family, access_variant):
    left = TICKET["left_panel_width"] + TICKET["content_padding"]
    width = PAGE_WIDTH - TICKET["left_panel_width"] - TICKET["right_panel_width"] - (2 * TICKET["content_padding"])
    top = PAGE_HEIGHT - (14 * mm)
    attendee_name = _text(position.attendee_name or _("Ticket holder"))
    date_line, time_line = _event_date_parts(event_object)
    venue_line = _text(getattr(event_object, "location", "") or getattr(position.order.event, "location", ""))
    presenter_line = _presenter_line(position.order.event)
    meta_gap = 4.5 * mm
    block_width = (width - (2 * meta_gap)) / 3

    pdf.saveState()
    pdf.setFillColor(family["muted"])
    _set_font(pdf, "mono", 6)
    pdf.drawString(left, top, "EVENT")

    event_name_y = top - 7 * mm
    event_lines = _split_lines(_text(event_object.name), _font_name("display"), 23, width, 2)
    pdf.setFillColor(family["headline"])
    _set_font(pdf, "display", 23)
    for idx, line in enumerate(event_lines):
        pdf.drawString(left, event_name_y - (idx * 6.2 * mm), line)

    _set_font(pdf, "body", 8.6)
    pdf.setFillColor(family["body_text"])
    presenter_y = event_name_y - ((max(len(event_lines), 1) - 1) * 6.2 * mm) - 5.3 * mm
    pdf.drawString(left, presenter_y, presenter_line[:52])

    divider_y = presenter_y - 3.4 * mm
    pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=0.06))
    pdf.line(left, divider_y, left + width, divider_y)

    pdf.setFillColor(family["muted"])
    _set_font(pdf, "mono", 6)
    pdf.drawString(left, divider_y - 5 * mm, "ATTENDEE")

    attendee_y = divider_y - 11.8 * mm
    attendee_lines = _split_lines(attendee_name, _font_name("display"), 17, width, 2)
    pdf.setFillColor(family["headline"])
    _set_font(pdf, "display", 17)
    for idx, line in enumerate(attendee_lines):
        pdf.drawString(left, attendee_y - (idx * 5.6 * mm), line)

    second_divider_y = attendee_y - ((max(len(attendee_lines), 1) - 1) * 5.6 * mm) - 4.2 * mm
    pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=0.06))
    pdf.line(left, second_divider_y, left + width, second_divider_y)

    details_top = 20 * mm
    _set_font(pdf, "mono", 6)
    pdf.setFillColor(family["muted"])
    pdf.drawString(left, details_top + 9 * mm, "DETAILS")

    detail_x = left
    for label, line in (
        ("DATE", date_line),
        ("TIME", time_line),
        ("VENUE", venue_line),
    ):
        if not line:
            continue
        pdf.setFillColor(family["muted"])
        _set_font(pdf, "mono", 6)
        pdf.drawString(detail_x, details_top, label)
        pdf.setFillColor(family["body_text"])
        _set_font(pdf, "body_medium", 8.2)
        for idx, value_line in enumerate(_split_lines(line, _font_name("body_medium"), 8.2, block_width, 2)):
            pdf.drawString(detail_x, details_top - 3.8 * mm - (idx * 3.45 * mm), value_line)
        detail_x += block_width + meta_gap
    pdf.restoreState()


def _draw_perforation(pdf, family):
    pdf.saveState()
    x = PAGE_WIDTH - TICKET["right_panel_width"] - (3 * mm)
    pdf.setDash(2, 2)
    pdf.setLineWidth(0.45)
    pdf.setStrokeColor(family["perf"])
    pdf.line(x, 10 * mm, x, PAGE_HEIGHT - 10 * mm)
    pdf.restoreState()


def _draw_corner_marks(pdf, family):
    color = family["corners"]
    size = 3 * mm
    inset = 3 * mm
    pdf.saveState()
    pdf.setStrokeColor(color)
    pdf.setLineWidth(0.6)
    for x, y, sx, sy in (
        (inset, PAGE_HEIGHT - inset, 1, -1),
        (PAGE_WIDTH - inset, PAGE_HEIGHT - inset, -1, -1),
        (inset, inset, 1, 1),
        (PAGE_WIDTH - inset, inset, -1, 1),
    ):
        pdf.line(x, y, x + (size * sx), y)
        pdf.line(x, y, x, y + (size * sy))
    pdf.restoreState()


def _draw_qr_panel(pdf, profile, family, scan_payload):
    zone_left = PAGE_WIDTH - TICKET["right_panel_width"] + (3 * mm)
    zone_bottom = 8 * mm
    zone_width = TICKET["right_panel_width"] - 6 * mm
    zone_height = PAGE_HEIGHT - 16 * mm

    pdf.saveState()
    pdf.setFillColor(family["qr_bg"])
    pdf.roundRect(zone_left, zone_bottom, zone_width, zone_height, 1.5 * mm, stroke=0, fill=1)
    pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=0.04))
    pdf.roundRect(zone_left, zone_bottom, zone_width, zone_height, 1.5 * mm, stroke=1, fill=0)

    # White box fills the full zone width
    box_w = zone_width
    box_h = box_w  # square

    # SCAN FOR ENTRY label sits below the white box
    scan_label = "SCAN FOR ENTRY"
    label_h = 4 * mm
    label_gap = 3 * mm

    # Center the group (box + gap + label) vertically in the zone
    group_h = box_h + label_gap + label_h
    group_bottom = zone_bottom + (zone_height - group_h) / 2

    label_y = group_bottom
    box_x = zone_left
    box_y = group_bottom + label_h + label_gap

    # QR fills white box minus padding on each side
    inner_pad = 2.5 * mm
    qr_size = box_w - (2 * inner_pad)
    qr_x = box_x + inner_pad
    qr_y = box_y + inner_pad

    pdf.setFillColor(colors.white)
    pdf.roundRect(box_x, box_y, box_w, box_h, 1.5 * mm, stroke=0, fill=1)

    qr = QrCodeWidget(scan_payload)
    qr.barFillColor = colors.black
    qr.barStrokeColor = colors.black
    bounds = qr.getBounds()
    bx, by, bx2, by2 = bounds
    nat_w = bx2 - bx
    nat_h = by2 - by
    sx = qr_size / nat_w
    sy = qr_size / nat_h
    grp = shapes.Group(qr, transform=(sx, 0, 0, sy, -bx * sx, -by * sy))
    drawing = shapes.Drawing(qr_size, qr_size)
    drawing.add(grp)
    renderPDF.draw(drawing, pdf, qr_x, qr_y)

    _set_font(pdf, "mono", 5.5)
    pdf.setFillColor(family["muted"])
    label_w = pdf.stringWidth(scan_label, _font_name("mono"), 5.5)
    pdf.drawString(zone_left + (zone_width - label_w) / 2, label_y, scan_label)
    pdf.restoreState()


def _event_date_parts(event_object):
    dt = getattr(event_object, "date_from", None)
    if not dt:
        return "", ""
    return dt.strftime("%d %b %Y"), dt.strftime("%I:%M %p").lstrip("0")


def _position_product_name(position):
    if position.variation_id and position.variation:
        return f"{_text(position.item.name)} - {_text(position.variation.value)}"
    return _text(position.item.name)


def _resolve_access_variant(position):
    haystack = " ".join(filter(None, [
        str(getattr(position.item, "name", "")),
        str(getattr(getattr(position, "variation", None), "value", "")),
    ])).lower()
    vip_tokens = ("vip", "premium", "backstage", "exclusive")
    return "vip" if any(token in haystack for token in vip_tokens) else "ga"


def _get_scan_payload(position):
    payload = getattr(position, "secret", "")
    if payload:
        return payload
    raise ValueError("Order position has no scan secret; cannot generate a scannable Ecube ticket.")


def _resolve_ticket_background(position, profile):
    if profile.use_hero_on_ticket:
        reader = _image_reader_from_event_asset(position.order.event, "hero_ticket_texture")
        if reader:
            return reader
    reader = _image_reader_from_event_asset(position.order.event, "background_texture_ticket")
    if reader:
        return reader
    if profile.background_texture_ticket_url:
        return _image_reader_from_url(profile.background_texture_ticket_url)
    return None


def _resolve_logo(position, profile):
    reader = _image_reader_from_event_asset(position.order.event, "logo_ticket")
    if reader:
        return reader
    if profile.logo_ticket_url:
        return _image_reader_from_url(profile.logo_ticket_url)
    if profile.logo_url:
        return _image_reader_from_url(profile.logo_url)
    return None


def _image_reader_from_event_asset(event, field_name):
    try:
        asset_pack = event.ecube_design_assets
    except Exception:
        logger.debug("No design asset pack for event %s", getattr(event, "slug", event))
        return None
    field = getattr(asset_pack, field_name, None)
    if not getattr(field, "name", ""):
        return None
    try:
        field.open("rb")
        content = field.read()
    except Exception:
        logger.debug("Could not read asset field %s", field_name)
        return None
    finally:
        try:
            field.close()
        except Exception:
            logger.debug("Could not close asset field %s", field_name)
    return ImageReader(BytesIO(content))


def _image_reader_from_url(url):
    if not url:
        return None
    media_prefix = MEDIA_URL.rstrip("/") + "/"
    if not url.startswith(media_prefix):
        return None
    local_path = MEDIA_ROOT / url[len(media_prefix):]
    if not local_path.exists() or not local_path.is_file():
        return None
    with open(local_path, "rb") as handle:
        return ImageReader(BytesIO(handle.read()))


def _hex_color(value):
    try:
        return colors.HexColor(value or "#0B1420")
    except Exception:
        logger.debug("Invalid hex color %r, using fallback", value)
        return colors.HexColor("#0B1420")


def _text(value):
    return force_str(value or "")


def _ticket_palette(profile, access_variant):
    accent = _hex_color(getattr(profile, "primary_color", "") or "#C8000A")
    secondary = _hex_color(getattr(profile, "secondary_color", "") or "#0B1017")
    accent_soft = _hex_color(getattr(profile, "accent_color", "") or "#F4E7E9")
    text = _hex_color(getattr(profile, "text_color", "") or "#F0ECE4")

    body_bg = _darken(secondary, 0.42)
    panel_bg = _blend(body_bg, colors.HexColor("#0E0E14"), 0.72)
    qr_bg = _darken(body_bg, 0.08)
    accent = _ensure_vibrant(accent, body_bg, boost=0.16 if access_variant == "vip" else 0.08)
    accent_soft = _blend(_ensure_legible(accent_soft, body_bg), text, 0.28)
    headline = _ensure_legible(text, body_bg, min_luminance=0.86)
    body_text = _blend(headline, accent_soft, 0.28)
    muted = _blend(body_text, body_bg, 0.58)

    return {
        "accent": accent,
        "accent_soft": accent_soft,
        "panel_bg": panel_bg,
        "panel_border": _alpha(headline, 0.08),
        "body_bg": body_bg,
        "qr_bg": qr_bg,
        "muted": muted,
        "body_text": body_text,
        "headline": headline,
        "watermark": _alpha(headline, 0.018),
        "perf": _alpha(accent_soft, 0.14),
        "corners": _alpha(accent_soft, 0.10),
        "laminate": colors.Color(0.02, 0.02, 0.03, alpha=0.66),
    }


def _presenter_line(event):
    organizer_name = _text(getattr(event.organizer, "name", ""))
    if not organizer_name:
        return "Presented by Ecube"
    return f"{organizer_name} presents"


def _format_price(position):
    amount = getattr(position, "price", None)
    if hasattr(amount, "gross"):
        amount = amount.gross
    currency = getattr(position.order.event, "currency", "") or "USD"
    if amount is None:
        return currency
    symbol_map = {
        "BDT": "৳",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
    }
    try:
        formatted = format_currency(amount, currency, locale="en_US")
        if currency in symbol_map:
            return formatted.replace(currency, symbol_map[currency]).replace("\xa0", "").strip()
        return formatted
    except Exception:
        return f"{currency} {amount}"


def _split_lines(text, font_name, size, width, limit):
    return simpleSplit(_text(text), font_name, size, width)[:limit]


def _alpha(color, alpha):
    return colors.Color(color.red, color.green, color.blue, alpha=alpha)


def _blend(color_a, color_b, ratio):
    ratio = max(0.0, min(1.0, ratio))
    inv = 1.0 - ratio
    return colors.Color(
        (color_a.red * inv) + (color_b.red * ratio),
        (color_a.green * inv) + (color_b.green * ratio),
        (color_a.blue * inv) + (color_b.blue * ratio),
    )


def _darken(color, amount):
    amount = max(0.0, min(1.0, amount))
    return colors.Color(
        color.red * (1.0 - amount),
        color.green * (1.0 - amount),
        color.blue * (1.0 - amount),
    )


def _lighten(color, amount):
    amount = max(0.0, min(1.0, amount))
    return colors.Color(
        color.red + ((1.0 - color.red) * amount),
        color.green + ((1.0 - color.green) * amount),
        color.blue + ((1.0 - color.blue) * amount),
    )


def _luminance(color):
    return (0.2126 * color.red) + (0.7152 * color.green) + (0.0722 * color.blue)


def _ensure_legible(color, bg, min_luminance=0.7):
    if _luminance(color) >= min_luminance:
        return color
    boosted = _lighten(color, 0.35)
    if _luminance(boosted) >= min_luminance:
        return boosted
    return _blend(boosted, colors.white, 0.35)


def _ensure_vibrant(color, bg, boost=0.1):
    color = _lighten(color, boost)
    if abs(_luminance(color) - _luminance(bg)) < 0.26:
        color = _lighten(color, 0.22)
    return color


def _ensure_brand_fonts():
    global _FONTS_READY
    if _FONTS_READY:
        return
    font_dir_candidates = [
        Path(__file__).resolve().parents[2] / "pretix_ticketing_portal" / "pretix_ticketing_portal" / "static" / "pretix_ticketing_portal" / "fonts",
        Path("/pretix/src/pretix_ticketing_portal/pretix_ticketing_portal/static/pretix_ticketing_portal/fonts"),
    ]
    available = set(pdfmetrics.getRegisteredFontNames())
    for alias, filename in FONT_FILES.items():
        if alias in available:
            continue
        for base in font_dir_candidates:
            candidate = base / filename
            if candidate.exists():
                try:
                    pdfmetrics.registerFont(TTFont(alias, str(candidate)))
                except Exception:
                    pass
                break
    _FONTS_READY = True


def _font_name(role):
    alias, fallback = FONT_ROLES[role]
    return alias if alias in pdfmetrics.getRegisteredFontNames() else fallback


def _set_font(pdf, role, size):
    pdf.setFont(_font_name(role), size)
