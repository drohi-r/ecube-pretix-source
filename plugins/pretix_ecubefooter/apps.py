from django.apps import AppConfig


class PluginApp(AppConfig):
    name = 'pretix_ecubefooter'
    verbose_name = 'Ecube Footer & Legal Pages'

    class PretixPluginMeta:
        name = 'Ecube Footer & Legal Pages'
        author = 'Ecube Inc.'
        description = 'Ecube branded footer with SSLCommerz compliance, legal pages (Terms, Privacy, Refund, About).'
        visible = True
        version = '2.0.0'

    def ready(self):
        from . import signals  # noqa
