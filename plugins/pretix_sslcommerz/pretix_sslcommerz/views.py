import logging

from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_scopes import scopes_disabled

from pretix.base.models import OrderPayment
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzReturnView(View):

    def post(self, request, organizer, event, payment):
        return self._handle(request, organizer, event, payment)

    def get(self, request, organizer, event, payment):
        return self._handle(request, organizer, event, payment)

    def _handle(self, request, organizer, event, payment):
        with scopes_disabled():
            payment_obj = get_object_or_404(
                OrderPayment,
                pk=payment,
                order__event__slug=event,
                order__event__organizer__slug=organizer,
            )
            order    = payment_obj.order
            ev       = order.event
            post     = request.POST.dict()
            status   = post.get('status') or request.GET.get('status', '')
            val_id   = post.get('val_id', '')

            logger.info('SSLCommerz callback. Payment=%s Status=%s', payment, status)

            order_url_kwargs = {
                'organizer': organizer,
                'event':     event,
                'order':     order.code,
                'secret':    order.secret,
            }

            if status == 'VALID':
                provider = payment_obj.payment_provider
                sandbox  = provider.settings.get('sandbox', as_type=bool)

                if not val_id:
                    logger.warning('No val_id in callback for payment %s', payment)
                    return HttpResponse('Missing val_id', status=400)

                # Validate against SSLCommerz API — checks status, tran_id, amount, currency
                if not provider.validate_payment_with_api(val_id, sandbox, payment_obj):
                    logger.warning(
                        'SSLCommerz validation FAILED for payment %s val_id %s',
                        payment, val_id
                    )
                    return HttpResponse('Payment validation failed', status=400)

                if payment_obj.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
                    logger.info('Payment %s already confirmed, skipping.', payment)
                    return redirect(
                        build_absolute_uri(ev, 'presale:event.order', kwargs=order_url_kwargs)
                    )

                try:
                    payment_obj.confirm()
                    logger.info('Payment %s confirmed successfully.', payment)
                except Exception as exc:
                    logger.exception('Error confirming payment %s: %s', payment, exc)
                    return HttpResponse('Confirmation error', status=500)

                return redirect(
                    build_absolute_uri(ev, 'presale:event.order', kwargs=order_url_kwargs)
                )

            elif status == 'FAILED':
                payment_obj.fail(info={'reason': post.get('error', 'Unknown')})
                logger.info('Payment %s failed.', payment)
                return redirect(
                    build_absolute_uri(ev, 'presale:event.order', kwargs=order_url_kwargs)
                )

            else:
                logger.info('Payment %s cancelled or unknown status: %s', payment, status)
                return redirect(
                    build_absolute_uri(ev, 'presale:event.checkout', kwargs={
                        'organizer': organizer,
                        'event':     event,
                        'step':      'payment',
                    })
                )


@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzCancelView(View):

    def post(self, request, organizer, event, payment):
        return self._handle(request, organizer, event, payment)

    def get(self, request, organizer, event, payment):
        return self._handle(request, organizer, event, payment)

    def _handle(self, request, organizer, event, payment):
        with scopes_disabled():
            payment_obj = get_object_or_404(
                OrderPayment,
                pk=payment,
                order__event__slug=event,
                order__event__organizer__slug=organizer,
            )
            ev = payment_obj.order.event
        logger.info('SSLCommerz payment %s cancelled by buyer.', payment)
        return redirect(
            build_absolute_uri(ev, 'presale:event.checkout', kwargs={
                'organizer': organizer,
                'event':     event,
                'step':      'payment',
            })
        )
