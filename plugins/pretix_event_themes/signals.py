from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_event_settings, nav_organizer
from pretix.presale.signals import global_html_head
from pretix.presale.signals import html_head as presale_html_head

THEME_FILES = {
    'bg': 'ecube-bhn-v2.css',
    'rb': 'ecube-rb-v2.css',
    'mb': 'ecube-mb-v2.css',
}
DEFAULT_THEME = 'bg'


def _theme_key_for_event(event):
    return event.settings.get('ecube_theme', '') or event.organizer.settings.get('ecube_theme', DEFAULT_THEME)


def _theme_key_for_organizer(organizer):
    return organizer.settings.get('ecube_theme', DEFAULT_THEME)


def _css_tag(theme_key):
    filename = THEME_FILES.get(theme_key, THEME_FILES[DEFAULT_THEME])
    return f'<link rel="stylesheet" type="text/css" href="/static/pretix_event_themes/{filename}?v=202603160011">'


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

    path = request.path
    parts = [p for p in path.strip('/').split('/') if p]
    if len(parts) == 1:
        try:
            from pretix.base.models import Organizer
            org = Organizer.objects.get(slug=parts[0])
            theme = _theme_key_for_organizer(org)
            return _css_tag(theme)
        except Exception:
            return ''
    return ''


@receiver(presale_html_head, dispatch_uid='pretix_event_themes_presale')
def presale_head(sender, request=None, **kwargs):
    theme = _theme_key_for_event(sender)
    bg = sender.settings.get('ecube_bg_url', '')

    output = _css_tag(theme)

    if bg:
        output += f'''
<meta name="event-themes-bg-url" content="{bg}">
<link rel="stylesheet" type="text/css" href="/static/pretix_event_themes/background-runtime.css?v=20260316001256"><script src="/static/pretix_event_themes/background.js?v=20260316002001"></script>
'''
    return output

