from django.urls import path
from django.views.generic import TemplateView

root_urlpatterns = [
    path("terms/", TemplateView.as_view(template_name="legal/terms.html"), name="legal_terms"),
    path("privacy/", TemplateView.as_view(template_name="legal/privacy.html"), name="legal_privacy"),
    path("refund/", TemplateView.as_view(template_name="legal/refund.html"), name="legal_refund"),
    path("about/", TemplateView.as_view(template_name="legal/about.html"), name="legal_about"),
    path("contact/", TemplateView.as_view(template_name="legal/contact.html"), name="legal_contact"),
]
