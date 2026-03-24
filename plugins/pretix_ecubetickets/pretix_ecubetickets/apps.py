import os

from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PLUGIN_LEVEL_EVENT, PluginConfig


class PluginApp(PluginConfig):
    name = "pretix_ecubetickets"
    verbose_name = "Ecube Tickets"
    default = True
    path = os.path.dirname(__file__)

    class PretixPluginMeta:
        name = _("Ecube Tickets")
        author = "Ecube"
        description = _("Branded PDF ticket output driven by Ecube design profiles")
        visible = True
        version = "1.0.0"
        category = "CUSTOMIZATION"
        compatibility = "pretix>=2024.0"
        level = PLUGIN_LEVEL_EVENT
        settings_links = []
        navigation_links = []

    def ready(self):
        from . import signals  # noqa
