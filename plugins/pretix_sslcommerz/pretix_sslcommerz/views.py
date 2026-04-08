import logging

from django.http import HttpResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_scopes import scopes_disabled

from pretix.base.models import OrderPayment
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger(__name__)


def _get_sslcommerz_payment(organizer, event, payment):
    payment_obj = get_object_or_404(
        OrderPayment,
        pk=payment,
        order__event__slug=event,
        order__event__organizer__slug=organizer,
    )
    provider = payment_obj.payment_provider
    if not provider or getattr(provider, 'identifier', None) != 'sslcommerz':
        logger.warning(
            'SSLCommerz callback rejected for non-SSLCommerz payment %s (provider=%s)',
            payment,
            getattr(provider, 'identifier', None),
        )
        raise Http404()
    return payment_obj, provider


def _store_sslcommerz_metadata(payment_obj, callback_data):
    info = dict(payment_obj.info_data or {})
    info['sslcommerz_meta'] = {
        'bank_tran_id': callback_data.get('bank_tran_id', ''),
        'card_type': callback_data.get('card_type', ''),
        'risk_level': callback_data.get('risk_level', ''),
        'risk_title': callback_data.get('risk_title', ''),
        'validated_status': callback_data.get('status', ''),
        'val_id': callback_data.get('val_id', ''),
    }
    payment_obj.info_data = info
    payment_obj.save(update_fields=['info'])


def _confirm_validated_payment(payment_obj, provider, callback_data):
    sandbox = provider.settings.get('sandbox', as_type=bool)
    val_id = callback_data.get('val_id', '')

    if not val_id:
        logger.warning('No val_id in SSLCommerz callback for payment %s', payment_obj.pk)
        return HttpResponse('Missing val_id', status=400)

    if not provider.verify_callback_hash(callback_data):
        logger.warning('SSLCommerz hash validation failed for payment %s', payment_obj.pk)
        return HttpResponse('Hash validation failed', status=400)

    if not provider.validate_payment_with_api(val_id, sandbox, payment_obj):
        logger.warning(
            'SSLCommerz validation FAILED for payment %s val_id %s',
            payment_obj.pk, val_id,
        )
        return HttpResponse('Payment validation failed', status=400)

    _store_sslcommerz_metadata(payment_obj, callback_data)

    risk_level = str(callback_data.get('risk_level', '')).strip()
    if risk_level == '1':
        logger.warning(
            'SSLCommerz marked payment %s as risky (%s)',
            payment_obj.pk,
            callback_data.get('risk_title', 'unknown'),
        )

    if payment_obj.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
        logger.info('Payment %s already confirmed, skipping.', payment_obj.pk)
        return None

    try:
        payment_obj.confirm()
        logger.info('Payment %s confirmed successfully.', payment_obj.pk)
    except Exception as exc:
        logger.exception('Error confirming payment %s: %s', payment_obj.pk, exc)
        return HttpResponse('Confirmation error', status=500)

    return None


@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzReturnView(View):

    def post(self, request, organizer, event, payment):
        return self._handle(request, organizer, event, payment)

    def get(self, request, organizer, event, payment):
        return self._handle(request, organizer, event, payment)

    def _handle(self, request, organizer, event, payment):
        with scopes_disabled():
            payment_obj, provider = _get_sslcommerz_payment(organizer, event, payment)
            order    = payment_obj.order
            ev       = order.event
            post     = request.POST.dict()
            status   = post.get('status') or request.GET.get('status', '')
            val_id   = post.get('val_id') or request.GET.get('val_id', '')

            logger.info('SSLCommerz callback. Payment=%s Status=%s', payment, status)

            order_url_kwargs = {
                'organizer': organizer,
                'event':     event,
                'order':     order.code,
                'secret':    order.secret,
            }

            if status == 'VALID':
                callback_data = request.POST.dict() if request.method == 'POST' else {}
                if callback_data:
                    error_response = _confirm_validated_payment(payment_obj, provider, callback_data)
                    if error_response is not None:
                        return error_response

                return redirect(
                    build_absolute_uri(ev, 'presale:event.order', kwargs=order_url_kwargs)
                )

            elif status == 'FAILED':
                logger.warning(
                    'Ignoring unauthenticated SSLCommerz FAILED callback for payment %s',
                    payment,
                )
                return redirect(
                    build_absolute_uri(ev, 'presale:event.checkout', kwargs={
                        'organizer': organizer,
                        'event':     event,
                        'step':      'payment',
                    })
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
            payment_obj, _provider = _get_sslcommerz_payment(organizer, event, payment)
            ev = payment_obj.order.event
        logger.info('SSLCommerz payment %s cancelled by buyer.', payment)
        return redirect(
            build_absolute_uri(ev, 'presale:event.checkout', kwargs={
                'organizer': organizer,
                'event':     event,
                'step':      'payment',
            })
        )


@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzIPNView(View):

    def post(self, request, organizer, event, payment):
        with scopes_disabled():
            payment_obj, provider = _get_sslcommerz_payment(organizer, event, payment)
            callback_data = request.POST.dict()
            status = callback_data.get('status', '')

            logger.info('SSLCommerz IPN. Payment=%s Status=%s', payment, status)

            if not provider.verify_callback_hash(callback_data):
                logger.warning('SSLCommerz IPN hash validation failed for payment %s', payment)
                return HttpResponse('Hash validation failed', status=400)

            if status == 'VALID':
                error_response = _confirm_validated_payment(payment_obj, provider, callback_data)
                if error_response is not None:
                    return error_response
            elif status in {'FAILED', 'CANCELLED', 'EXPIRED', 'UNATTEMPTED'}:
                _store_sslcommerz_metadata(payment_obj, callback_data)
                if payment_obj.state not in {
                    OrderPayment.PAYMENT_STATE_CONFIRMED,
                    OrderPayment.PAYMENT_STATE_FAILED,
                }:
                    payment_obj.fail(info={'reason': status})
                    logger.info('Payment %s marked failed from authenticated IPN.', payment)
            else:
                logger.info('Ignoring unknown SSLCommerz IPN status for payment %s: %s', payment, status)

        return HttpResponse('OK')
