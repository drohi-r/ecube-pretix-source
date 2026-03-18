from django.apps import AppConfig

class PluginApp(AppConfig):
    name = 'pretix_sslcommerz'
    verbose_name = 'SSLCommerz for pretix'

    class PretixPluginMeta:
        name = 'SSLCommerz'
        author = 'Unraid Admin'
        description = 'Accept payments via SSLCommerz.'
        visible = True
        version = '1.0.0'

    def ready(self):
        from . import signals  # NOQA
