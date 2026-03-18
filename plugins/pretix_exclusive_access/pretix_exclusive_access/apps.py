from django.utils.translation import gettext_lazy as _

try:
    from pretix.base.plugins import PluginConfig, PLUGIN_LEVEL_EVENT
except ImportError:
    raise RuntimeError("Please use a compatible pretix version for this plugin.")


class PluginApp(PluginConfig):
    name = "pretix_exclusive_access"
    verbose_name = _("Exclusive Access")

    class PretixPluginMeta:
        name = _("Exclusive Access")
        author = "Ecube"
        version = "1.0.0"
        category = "FEATURE"
        visible = True
        featured = False
        restricted = False
        level = PLUGIN_LEVEL_EVENT
        description = _("Approval-gated access applications for protected items.")
        compatibility = "pretix>=2025.0"
        settings_links = []
        navigation_links = []

    def ready(self):
        from . import signals  # noqa

