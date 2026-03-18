import os

from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PluginConfig, PLUGIN_LEVEL_EVENT


class PluginApp(PluginConfig):
    name = "pretix_ecube_access"
    verbose_name = "Ecube Access"
    default = True
    path = os.path.dirname(__file__)

    class PretixPluginMeta:
        name = _("Ecube Access")
        author = "Ecube"
        description = _("Unified scanning and door orchestration")
        visible = True
        version = "1.0.0"
        category = "FEATURE"
        compatibility = "pretix>=2024.0"
        level = PLUGIN_LEVEL_EVENT
        settings_links = []
        navigation_links = []

    def ready(self):
        from . import signals  # noqa

