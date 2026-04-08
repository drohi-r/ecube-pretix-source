from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from pretix.presale.signals import global_html_head, global_html_footer, checkout_confirm_messages


@receiver(global_html_head, dispatch_uid="ecube_footer_css_v3")
def ecube_footer_css(sender, request, **kwargs):
    return '<link rel="stylesheet" type="text/css" href="/static/pretix_ecubefooter/ecube-footer.css?v=3.8">'


@receiver(global_html_footer, dispatch_uid="ecube_branding_vFinal")
def ecube_branding_vFinal(sender, request, **kwargs):
    return '''<div id="ecube-branding-vFinal">
<div class="ecube-footer-banner">
    <img src="/static/pretix_ecubefooter/sslcommerz-pay-with.jpg"
         alt="Pay with SSLCommerz - Visa, Mastercard, bKash, Nagad, Rocket and more"
         loading="lazy">
</div>
<div class="ecube-footer-mid">
    &copy; 2026 Ecube Entertainment Ltd. &middot;
    Powered by <a href="https://pretix.eu" target="_blank" rel="noopener">pretix</a> &middot;
    Customized by <a href="https://ecube-entertainment.com" target="_blank" rel="noopener">Ecube</a> &middot;
    <a href="https://ecube-entertainment.com/about-platform" target="_blank" rel="noopener">Source &amp; Modifications</a>
</div>
<div class="ecube-footer-legal">
    <a href="/about/">About</a>
    <span class="ecube-footer-legal-sep">&middot;</span>
    <a href="/contact/">Contact</a>
    <span class="ecube-footer-legal-sep">&middot;</span>
    <a href="/privacy/">Privacy</a>
    <span class="ecube-footer-legal-sep">&middot;</span>
    <a href="/terms/">Terms</a>
    <span class="ecube-footer-legal-sep">&middot;</span>
    <a href="/refund/">Refund Policy</a>
</div>
</div>'''


@receiver(checkout_confirm_messages, dispatch_uid="ecube_checkout_consent")
def ecube_checkout_consent(sender, **kwargs):
    return {
        'ecube_terms_consent': (
            'I have read and agree to the '
            '<a href="/terms/" target="_blank">Terms &amp; Conditions</a>, '
            '<a href="/privacy/" target="_blank">Privacy Policy</a>, and '
            '<a href="/refund/" target="_blank">Return &amp; Refund Policy</a> '
            'of Ecube Entertainment Ltd.'
        )
    }
