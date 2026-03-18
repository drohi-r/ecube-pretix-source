from django.apps import AppConfig


class PluginApp(AppConfig):
    name = 'pretix_ecubefooter'
    verbose_name = 'Ecube Footer'

    class PretixPluginMeta:
        name = 'Ecube Footer'
        author = 'Ecube Inc.'
        description = 'Replaces default Pretix footer with Ecube branding and AGPLv3-compliant source link.'
        visible = True
        version = '1.0.0'

    def ready(self):
        from . import signals  # noqa

