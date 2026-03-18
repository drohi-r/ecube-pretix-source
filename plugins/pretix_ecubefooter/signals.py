from django.dispatch import receiver
from pretix.presale.signals import global_html_head, global_html_footer

@receiver(global_html_head, dispatch_uid="ecube_absolute_nuke_vFinal")
def ecube_absolute_nuke(sender, request, **kwargs):
    return ''

@receiver(global_html_footer, dispatch_uid="ecube_branding_vFinal")
def ecube_branding_vFinal(sender, request, **kwargs):
    return '<div id="ecube-branding-vFinal"><div>Powered by <a href="https://pretix.eu" target="_blank" rel="noopener">pretix</a> &middot; Customized by <a href="https://ecube-entertainment.com" target="_blank" rel="noopener">Ecube</a></div><div>&copy; 2026 Ecube Entertainment Ltd.</div><div><a href="https://ecube-entertainment.com/about-platform" target="_blank" rel="noopener">Source &amp; Modifications</a></div></div>'
