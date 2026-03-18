from django.utils.translation import gettext_lazy as _


class PretixPluginMeta:
    name = _('SSLCommerz')
    author = 'Ecube Entertainment'
    version = '1.0.0'
    description = _('Accept payments via SSLCommerz in pretix.')
    visible = True
    restricted = False
    urls = 'pretix_sslcommerz.urls'


default_app_config = 'pretix_sslcommerz.apps.PluginApp'
