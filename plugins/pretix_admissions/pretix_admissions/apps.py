import os

from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PluginConfig, PLUGIN_LEVEL_EVENT


class PluginApp(PluginConfig):
    name = "pretix_admissions"
    verbose_name = "Pretix Admissions"
    default = True
    path = os.path.dirname(__file__)

    class PretixPluginMeta:
        name = _("Credentials")
        author = "Ecube"
        description = _("Standalone admissions credentials and scan logging")
        visible = True
        version = "1.2.0"
        category = "FEATURE"
        compatibility = "pretix>=2024.0"
        level = PLUGIN_LEVEL_EVENT
        settings_links = []
        navigation_links = []

    def ready(self):
        from . import signals  # noqa

