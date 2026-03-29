import logging
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.utils import timezone
from django_scopes import scopes_disabled
from pretix.base.models import Event
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger(__name__)


PORTAL_VISIBILITY_CHOICES = (
    ("auto", "Auto"),
    ("hidden", "Hidden"),
    ("listed", "Listed"),
)

PORTAL_LABEL_CHOICES = (
    ("", "No label"),
    ("invite_only", "Invite only"),
    ("application", "Application required"),
)

PORTAL_CATEGORY_CHOICES = (
    ("", "No category"),
    ("Music", "Music"),
    ("Art & Culture", "Art & Culture"),
    ("Corporate", "Corporate"),
)

PORTAL_CATEGORIES = [choice[0] for choice in PORTAL_CATEGORY_CHOICES if choice[0]]
MAX_DEFAULT_SORT = 10 ** 9


@dataclass
class PortalEventEntry:
    event: Event
    is_public: bool
    is_listed_private: bool
    featured: bool
    hero_priority: int
    visibility: str
    label: str
    category: str
    sort_order: int
    url: str
    sort_datetime: Optional[timezone.datetime]
    sale_state: str
    sale_state_label: str
    primary_badge_class: str
    accent_class: str
    badges: list
    minimum_price: Optional[Decimal]
    price_display: str
    price_table_display: str
    is_free: bool
    primary_badge_label: str
    availability_percent: Optional[int]
    has_availability_bar: bool
    availability_display: str
    access_mode_label: str
    image_gradient: str
    image_url: str
    search_blob: str


def build_portal_context(category_filter: str = ""):
    normalized_category = category_filter if category_filter in PORTAL_CATEGORIES else ""

    events = _load_candidate_events()
    entries = []
    for event in events:
        entry = _build_event_entry(event)
        if not entry:
            continue
        entries.append(entry)

    if normalized_category:
        filtered_entries = [entry for entry in entries if entry.category == normalized_category]
    else:
        filtered_entries = list(entries)

    filtered_entries.sort(key=_portal_sort_key)

    featured_entries = [entry for entry in filtered_entries if entry.featured]
    # Hero selection: featured entries with hero_priority > 0 win (lowest first),
    # then remaining featured by sort key, then first entry as fallback
    prioritized = [e for e in featured_entries if e.hero_priority > 0]
    prioritized.sort(key=lambda e: e.hero_priority)
    unprioritized = [e for e in featured_entries if e.hero_priority == 0]
    unprioritized.sort(key=_portal_sort_key)
    hero_candidates = prioritized + unprioritized
    hero_entry = hero_candidates[0] if hero_candidates else (filtered_entries[0] if filtered_entries else None)

    category_counts = []
    for category in PORTAL_CATEGORIES:
        category_counts.append({
            "label": category,
            "query_value": category,
            "count": sum(1 for entry in entries if entry.category == category),
            "active": category == normalized_category,
        })

    filter_tabs = _build_filter_tabs(filtered_entries)
    sections = _build_sections(filtered_entries)
    ticker_items = _build_ticker_items(entries)

    return {
        "hero_entry": hero_entry,
        "portal_entries": filtered_entries,
        "portal_sections": sections,
        "portal_category_filter": normalized_category,
        "portal_category_counts": category_counts,
        "portal_filter_tabs": filter_tabs,
        "portal_ticker_items": ticker_items,
        "portal_total_count": len(entries),
        "portal_filtered_count": len(filtered_entries),
    }


def _load_candidate_events():
    with scopes_disabled():
        return list(
            Event.objects.select_related("organizer")
            .prefetch_related("items__quotas")
            .order_by("date_from", "organizer__slug", "slug")
        )


def _build_event_entry(event):
    if not getattr(event, "live", True):
        return None

    visibility = _normalize_choice(
        event.settings.get("portal_visibility", default="auto"),
        {"auto", "hidden", "listed"},
        "auto",
    )
    if visibility == "hidden":
        return None

    is_public = _event_is_public(event)
    is_listed_private = visibility == "listed" and not is_public
    if not is_public and not is_listed_private:
        return None

    category = _normalize_choice(
        event.settings.get("portal_category", default=""),
        set(PORTAL_CATEGORIES) | {""},
        "",
    )
    label = _normalize_choice(
        event.settings.get("portal_label", default=""),
        {"", "invite_only", "application"},
        "",
    )
    featured = bool(event.settings.get("portal_featured", as_type=bool, default=False))
    hero_priority = _coerce_int(event.settings.get("portal_hero_priority", as_type=int, default=0))
    sort_order = _coerce_int(event.settings.get("portal_sort_order", as_type=int, default=0))
    show_image = event.settings.get("portal_show_image", as_type=bool, default=True)
    if show_image is None:
        show_image = True
    items = list(getattr(event, "_prefetched_objects_cache", {}).get("items", []))

    minimum_price = _minimum_price(items)
    sale_state = _derive_sale_state(event, items)
    availability_percent = _derive_availability_percent(items)

    badges = []
    accent_class = "portal-card-default"
    primary_badge_class = "badge-upcoming"

    if featured:
        badges.append({"label": "Featured", "class": "badge-featured"})
        accent_class = "portal-card-featured"
        primary_badge_class = "badge-featured"

    if sale_state == "ON_SALE":
        badges.append({"label": "On Sale", "class": "badge-sale"})
        if accent_class == "portal-card-default":
            accent_class = "portal-card-sale"
            primary_badge_class = "badge-sale"
    elif sale_state == "UPCOMING":
        badges.append({"label": "Upcoming", "class": "badge-upcoming"})
        if accent_class == "portal-card-default":
            primary_badge_class = "badge-upcoming"
    elif sale_state == "SOLD_OUT":
        badges.append({"label": "Sold Out", "class": "badge-sold"})
        accent_class = "portal-card-sold"
        primary_badge_class = "badge-sold"

    if minimum_price == Decimal("0"):
        badges.append({"label": "Free", "class": "badge-free"})
        if sale_state != "SOLD_OUT":
            accent_class = "portal-card-sale"
            primary_badge_class = "badge-free"

    if label == "invite_only":
        badges.append({"label": "Invite Only", "class": "badge-invite"})
        if sale_state != "SOLD_OUT":
            accent_class = "portal-card-invite"
            primary_badge_class = "badge-invite"
    elif label == "application":
        badges.append({"label": "Application Required", "class": "badge-invite"})
        if sale_state != "SOLD_OUT" and accent_class == "portal-card-default":
            accent_class = "portal-card-invite"
            primary_badge_class = "badge-invite"

    if is_listed_private:
        badges.append({"label": "Listed Private", "class": "badge-hidden"})
        if sale_state != "SOLD_OUT" and accent_class == "portal-card-default":
            primary_badge_class = "badge-hidden"

    access_mode_label = "Public"
    if label == "invite_only":
        access_mode_label = "Invite Only"
    elif label == "application":
        access_mode_label = "Application"
    elif is_listed_private:
        access_mode_label = "Listed Private"

    image_url = ""
    if show_image:
        custom_url = event.settings.get("portal_custom_image_url", default="")
        image_url = custom_url or _event_image_url(event)

    return PortalEventEntry(
        event=event,
        is_public=is_public,
        is_listed_private=is_listed_private,
        featured=featured,
        hero_priority=hero_priority,
        visibility=visibility,
        label=label,
        category=category,
        sort_order=sort_order,
        url=build_absolute_uri(event, "presale:event.index"),
        sort_datetime=_event_sort_datetime(event),
        sale_state=sale_state,
        sale_state_label=_sale_state_label(sale_state),
        primary_badge_class=primary_badge_class,
        accent_class=accent_class,
        badges=badges,
        minimum_price=minimum_price,
        price_display=_price_display(minimum_price, label, is_listed_private),
        price_table_display=_price_table_display(minimum_price, label, is_listed_private),
        is_free=minimum_price == Decimal("0"),
        primary_badge_label=badges[0]["label"] if badges else "",
        availability_percent=availability_percent,
        has_availability_bar=availability_percent is not None,
        availability_display=f"{availability_percent}%" if availability_percent is not None else "",
        access_mode_label=access_mode_label,
        image_gradient=_image_gradient(event, sale_state, category, label, featured),
        image_url=image_url,
        search_blob=_search_blob(event, category, access_mode_label),
    )


def _normalize_choice(value, allowed, default):
    if value in allowed:
        return value
    return default


def _coerce_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _event_is_public(event):
    for attr in ("is_public", "public"):
        value = getattr(event, attr, None)
        if callable(value):
            try:
                value = value()
            except TypeError:
                value = None
        if isinstance(value, bool):
            return value
    return bool(getattr(event, "live", False))


def _event_sort_datetime(event):
    return getattr(event, "date_from", None) or getattr(event, "date_to", None)


def _minimum_price(items):
    prices = []
    for item in items:
        if not getattr(item, "active", True):
            continue
        price = getattr(item, "default_price", None)
        try:
            if price is not None:
                prices.append(Decimal(price))
        except (TypeError, InvalidOperation):
            continue
    if not prices:
        return None
    return min(prices)


def _item_available_now(item, now):
    if not getattr(item, "active", True):
        return False

    method = getattr(item, "is_available", None)
    if callable(method):
        for kwargs in ({}, {"now": now}):
            try:
                value = method(**kwargs)
            except TypeError:
                continue
            except Exception:
                value = None
            if isinstance(value, bool):
                return value

    available_from = getattr(item, "available_from", None)
    if available_from and available_from > now:
        return False
    available_until = getattr(item, "available_until", None)
    if available_until and available_until < now:
        return False
    return True


def _quota_numbers(quota):
    available = None
    size = getattr(quota, "size", None)

    for method_name in ("availability", "availability_count"):
        method = getattr(quota, method_name, None)
        if not callable(method):
            continue
        for kwargs in ({}, {"count_waitinglist": False}):
            try:
                raw = method(**kwargs)
            except TypeError:
                continue
            except Exception:
                raw = None
            parsed = _parse_availability_value(raw)
            if parsed is not None:
                available = parsed
                break
        if available is not None:
            break

    if available is None:
        for attr in ("available_number", "available", "availability_number"):
            parsed = _parse_availability_value(getattr(quota, attr, None))
            if parsed is not None:
                available = parsed
                break

    try:
        size = int(size) if size is not None else None
    except (TypeError, ValueError):
        size = None

    return available, size


def _parse_availability_value(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("available_number", "available", "availability"):
            if key in value:
                return _parse_availability_value(value[key])
    if hasattr(value, "available_number"):
        return _parse_availability_value(getattr(value, "available_number", None))
    if hasattr(value, "available"):
        return _parse_availability_value(getattr(value, "available", None))
    return None


def _derive_sale_state(event, items):
    now = timezone.now()
    any_currently_available = False
    saw_quota = False
    saw_availability = False
    all_known_availability_zero = True

    for item in items:
        if not getattr(item, "active", True):
            continue
        if _item_available_now(item, now):
            any_currently_available = True

        quotas = list(getattr(item, "_prefetched_objects_cache", {}).get("quotas", []))
        for quota in quotas:
            available, _size = _quota_numbers(quota)
            saw_quota = True
            if available is None:
                continue
            saw_availability = True
            if available > 0:
                all_known_availability_zero = False
            elif available < 0:
                all_known_availability_zero = False

    if any_currently_available and (not saw_availability or not all_known_availability_zero):
        return "ON_SALE"
    if saw_quota and saw_availability and all_known_availability_zero:
        return "SOLD_OUT"

    event_date = _event_sort_datetime(event)
    if event_date and event_date > now:
        return "UPCOMING"
    return "ON_SALE"


def _derive_availability_percent(items):
    total_size = 0
    total_available = 0
    saw_usable_quota = False

    for item in items:
        if not getattr(item, "active", True):
            continue
        quotas = list(getattr(item, "_prefetched_objects_cache", {}).get("quotas", []))
        for quota in quotas:
            available, size = _quota_numbers(quota)
            if available is None or size is None or size <= 0:
                continue
            if available < 0:
                continue
            total_size += size
            total_available += min(available, size)
            saw_usable_quota = True

    if not saw_usable_quota or total_size <= 0:
        return None

    percent = round((total_available / total_size) * 100)
    return max(0, min(100, percent))


def _sale_state_label(sale_state):
    labels = {
        "ON_SALE": "On Sale",
        "UPCOMING": "Upcoming",
        "SOLD_OUT": "Sold Out",
    }
    return labels.get(sale_state, "On Sale")


def _price_display(minimum_price, label, is_listed_private):
    if minimum_price == Decimal("0"):
        return "Free Entry"
    if minimum_price is not None:
        quantized = minimum_price.quantize(Decimal("1")) if minimum_price == minimum_price.to_integral() else minimum_price
        return f"BDT {quantized:,}"
    if label == "application" or is_listed_private:
        return "Application"
    return "TBA"


def _price_table_display(minimum_price, label, is_listed_private):
    if minimum_price == Decimal("0"):
        return "Free Entry"
    if minimum_price is not None:
        quantized = minimum_price.quantize(Decimal("1")) if minimum_price == minimum_price.to_integral() else minimum_price
        return f"{quantized:,}"
    if label == "application" or is_listed_private:
        return "Application"
    return "TBA"


def _portal_sort_key(entry):
    return (
        0 if entry.sort_order > 0 else 1,
        entry.sort_order if entry.sort_order > 0 else MAX_DEFAULT_SORT,
        entry.sort_datetime or datetime.max.replace(tzinfo=dt_timezone.utc),
        entry.event.organizer.slug,
        entry.event.slug,
    )


def _build_filter_tabs(entries):
    return [
        {"key": "all", "label": "All", "count": len(entries), "active": True},
        {"key": "on_sale", "label": "On Sale", "count": sum(1 for e in entries if e.sale_state == "ON_SALE")},
        {"key": "upcoming", "label": "Upcoming", "count": sum(1 for e in entries if e.sale_state == "UPCOMING")},
        {"key": "free", "label": "Free", "count": sum(1 for e in entries if e.is_free)},
        {"key": "exclusive", "label": "Exclusive", "count": sum(1 for e in entries if _is_exclusive(e))},
    ]


def _build_sections(entries):
    on_sale = [entry for entry in entries if entry.sale_state == "ON_SALE" and not _is_exclusive(entry)]
    upcoming = [entry for entry in entries if entry.sale_state == "UPCOMING" and not _is_exclusive(entry)]
    exclusive = [entry for entry in entries if _is_exclusive(entry)]
    sold_out = [entry for entry in entries if entry.sale_state == "SOLD_OUT"]

    sections = [
        {"key": "on_sale", "title": "On Sale Now", "entries": on_sale},
        {"key": "upcoming", "title": "Coming Soon", "entries": upcoming},
        {"key": "exclusive", "title": "Special Access", "entries": exclusive},
        {"key": "sold_out", "title": "Archive / Sold Out", "entries": sold_out},
    ]
    return [section for section in sections if section["entries"]]


def _build_ticker_items(entries):
    items = []
    for entry in entries[:8]:
        label = entry.sale_state_label.upper()
        if entry.is_free:
            label = "FREE ENTRY"
        elif _is_exclusive(entry):
            label = entry.access_mode_label.upper()
        when = entry.event.date_from.strftime("%d %b").upper() if entry.event.date_from else "DATE TBA"
        items.append(f"{_as_text(entry.event.name).upper()} — {when} — {label}")
    return items


def _is_exclusive(entry):
    return entry.label in {"invite_only", "application"} or entry.is_listed_private


def _event_image_url(event):
    try:
        from pretix_event_themes.services.resolver import resolve_design_profile
        profile = resolve_design_profile(event)
        if profile.hero_card_16x9_url:
            return profile.hero_card_16x9_url
    except Exception:
        pass
    # Fallback to Pretix header image
    logo = event.settings.get("logo_image")
    if logo and hasattr(logo, "url"):
        return logo.url
    return ""


def _image_gradient(event, sale_state, category, label, featured):
    category_key = (category or "").lower()
    if featured:
        return "linear-gradient(135deg, #28110f 0%, #44211b 38%, #0f1118 100%)"
    if label == "invite_only":
        return "linear-gradient(135deg, #170d24 0%, #3b2358 45%, #090a12 100%)"
    if label == "application":
        return "linear-gradient(135deg, #0a1222 0%, #17324c 44%, #090a12 100%)"
    if sale_state == "SOLD_OUT":
        return "linear-gradient(135deg, #16161c 0%, #23232b 44%, #0a0a0d 100%)"
    if category_key == "music":
        return "linear-gradient(135deg, #1a0a1e 0%, #0e1a2e 50%, #0a0e1a 100%)"
    if category_key == "art & culture":
        return "linear-gradient(135deg, #1d1207 0%, #4c2715 42%, #120e0b 100%)"
    if category_key == "corporate":
        return "linear-gradient(135deg, #0b1116 0%, #163140 44%, #0a0d11 100%)"
    if sale_state == "UPCOMING":
        return "linear-gradient(135deg, #0d1420 0%, #16364b 48%, #0a0d12 100%)"
    return "linear-gradient(135deg, #151015 0%, #2b1418 44%, #090a10 100%)"


def _search_blob(event, category, access_mode_label):
    parts = [
        _as_text(getattr(event, "name", "")),
        _as_text(getattr(event, "location", "")),
        _as_text(category),
        _as_text(access_mode_label),
        _as_text(getattr(event.organizer, "name", "")),
    ]
    return " ".join(parts).strip()


def _as_text(value):
    if value is None:
        return ""
    return str(value)
