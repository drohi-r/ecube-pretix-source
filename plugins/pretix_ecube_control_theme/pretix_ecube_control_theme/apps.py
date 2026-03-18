import os

from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "pretix_ecube_control_theme"
    verbose_name = "Ecube Backend UI"
    default = True
    path = os.path.dirname(__file__)

    class PretixPluginMeta:
        name = _("Ecube Backend UI")
        author = "Ecube"
        description = _("Global control-panel design system and UI shell for Ecube Pretix extensions.")
        visible = True
        version = "1.0.0"
        category = "CUSTOMIZATION"
        compatibility = "pretix>=2025.0"
        settings_links = []
        navigation_links = []

    def ready(self):
        from . import signals  # noqa

