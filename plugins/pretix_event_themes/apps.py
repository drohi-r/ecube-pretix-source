from django.apps import AppConfig


class PluginApp(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "pretix_event_themes"
    label = "pretix_event_themes"
    verbose_name = "Themes"

    class PretixPluginMeta:
        name = "Themes"
        author = "Ecube Inc."
        description = "Theme selection and per-event background images."
        visible = True
        version = "1.0.0"
        category = "CUSTOMIZATION"
        compatibility = "pretix>=2023.1"

    def ready(self):
        import pretix_event_themes.signals  # noqa

