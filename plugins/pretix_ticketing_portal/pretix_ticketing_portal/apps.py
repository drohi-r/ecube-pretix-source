import os

from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PLUGIN_LEVEL_EVENT, PluginConfig


class PluginApp(PluginConfig):
    name = "pretix_ticketing_portal"
    verbose_name = _("Ticketing Portal")
    default = True
    path = os.path.dirname(__file__)

    class PretixPluginMeta:
        name = _("Ticketing Portal")
        author = "Ecube"
        description = _("Installation-wide ticketing portal homepage and per-event portal settings.")
        visible = True
        version = "1.0.0"
        category = "CUSTOMIZATION"
        compatibility = "pretix>=2024.0"
        level = PLUGIN_LEVEL_EVENT
        settings_links = []
        navigation_links = []

    def ready(self):
        from . import signals  # noqa
