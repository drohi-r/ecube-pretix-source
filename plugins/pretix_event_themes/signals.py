from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_event_settings, nav_organizer
from pretix.presale.signals import global_html_head
from pretix.presale.signals import html_head as presale_html_head

from .services.resolver import resolve_design_profile

THEME_FILES = {
    'gilt': 'ecube-gilt-v1.css',
    'crimson': 'ecube-crimson-v1.css',
    'voltage': 'ecube-voltage-v1.css',
    'nexus': 'ecube-nexus-v1.css',
    'aurora': 'ecube-aurora-v1.css',
    'ember': 'ecube-ember-v1.css',
    'specter': 'ecube-specter-v1.css',
}
DEFAULT_THEME = 'gilt'


def _normalize_theme_key(value):
    from .theme_config import LEGACY_PRESET_ALIASES
    return LEGACY_PRESET_ALIASES.get(value, value)


def _theme_key_for_event(event):
    value = event.settings.get('ecube_theme', '') or event.organizer.settings.get('ecube_theme', DEFAULT_THEME)
    return _normalize_theme_key(value)


def _theme_key_for_organizer(organizer):
    return _normalize_theme_key(organizer.settings.get('ecube_theme', DEFAULT_THEME))


def _css_tag(theme_key):
    filename = THEME_FILES.get(theme_key, THEME_FILES[DEFAULT_THEME])
    return f'<link rel="stylesheet" type="text/css" href="/static/pretix_event_themes/{filename}?v=20260409-v7">'


@receiver(nav_event_settings, dispatch_uid='pretix_event_themes_nav_event')
def navbar_event_settings(sender, request=None, **kwargs):
    return [{
        'label': _('Themes'),
        'url': reverse('plugins:pretix_event_themes:event_settings', kwargs={
            'organizer': request.organizer.slug,
            'event': request.event.slug,
        }),
        'active': 'settings/themes' in request.path,
    }]


@receiver(nav_organizer, dispatch_uid='pretix_event_themes_nav_org')
def navbar_organizer_settings(sender, request=None, **kwargs):
    return [{
        'label': _('Themes'),
        'url': reverse('plugins:pretix_event_themes:organizer_settings', kwargs={
            'organizer': request.organizer.slug,
        }),
        'active': 'settings/themes' in request.path,
    }]


@receiver(global_html_head, dispatch_uid='pretix_event_themes_global')
def global_head(sender, request=None, **kwargs):
    if not request:
        return ''

    # Skip event pages — presale_html_head handles those with per-event theme
    if getattr(request, 'event', None):
        return ''

    path = request.path
    parts = [p for p in path.strip('/').split('/') if p]
    if not parts:
        return ''

    # Organizer-level pages only (account, login, etc.)
    try:
        from pretix.base.models import Organizer
        org = Organizer.objects.get(slug=parts[0])
        theme = _theme_key_for_organizer(org)
        return _css_tag(theme)
    except Exception:
        return ''


@receiver(presale_html_head, dispatch_uid='pretix_event_themes_presale')
def presale_head(sender, request=None, **kwargs):
    profile = resolve_design_profile(sender)
    theme = _normalize_theme_key(profile.page_theme_slug)
    preset = _normalize_theme_key(profile.profile_slug or theme)
    bg = profile.background_texture_url or sender.settings.get('ecube_bg_url', '')

    output = _css_tag(theme)

    LAYOUT_PRESETS = ('nexus', 'aurora', 'ember', 'specter')
    LAYOUT_FILES = {
        'nexus': 'ecube-nexus-layout.css',
        'aurora': 'ecube-aurora-layout.css',
        'ember': 'ecube-ember-layout.css',
        'specter': 'ecube-specter-layout.css',
    }
    if preset in LAYOUT_PRESETS:
        # Shared reset first (unlocks .main-box container), then theme-specific layout
        if preset != 'nexus':  # nexus layout has its own reset via :has()
            output += '<link rel="stylesheet" type="text/css" href="/static/pretix_event_themes/ecube-layout-reset.css?v=20260409-v7">'
        output += f'<link rel="stylesheet" type="text/css" href="/static/pretix_event_themes/{LAYOUT_FILES[preset]}?v=20260409-v7">'

    if bg:
        output += f'''
<meta name="event-themes-bg-url" content="{bg}">
<link rel="stylesheet" type="text/css" href="/static/pretix_event_themes/background-runtime.css?v=20260316001256"><script src="/static/pretix_event_themes/background.js?v=20260316002001"></script>
'''
    return output
