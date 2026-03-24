from django.db.models.signals import post_save
from django.dispatch import receiver
from pretix.base.signals import register_html_mail_renderers

from .email_defaults import apply_email_defaults
from .renderer import EcubeMailRenderer


@receiver(register_html_mail_renderers, dispatch_uid="pretix_ecubemail_renderer")
def html_mail_renderers(sender, **kwargs):
    return [EcubeMailRenderer]


@receiver(post_save, sender="pretixbase.Organizer", dispatch_uid="ecubemail_organizer_defaults")
def on_organizer_created(sender, instance, created, **kwargs):
    """Auto-apply Ecube email defaults when a new organizer is created.

    Writes defaults to organizer-level settings so all events inherit them.
    Per-event overrides set via Settings → E-mail still take precedence.
    Existing organizers can be backfilled with:
        python -m pretix setup_ecube_email_defaults
    """
    if not created:
        return
    try:
        apply_email_defaults(instance, force=False)
    except Exception:
        pass
