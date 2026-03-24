from django.dispatch import receiver
from pretix.base.signals import register_ticket_outputs

from .ticketoutput import EcubeTicketOutput


@receiver(register_ticket_outputs, dispatch_uid="pretix_ecubetickets_output")
def ticket_outputs(sender, **kwargs):
    return EcubeTicketOutput
