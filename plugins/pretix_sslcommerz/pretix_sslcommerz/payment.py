import hashlib
import logging
from collections import OrderedDict

import requests
from django import forms
from django.utils.translation import gettext_lazy as _

from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger(__name__)


class SSLCommerzPayment(BasePaymentProvider):
    identifier = 'sslcommerz'
    verbose_name = _('SSLCommerz')
    public_name = _('Pay with SSLCommerz')

    @property
    def settings_form_fields(self):
        fields = [
            ('store_id', forms.CharField(
                label=_('Store ID'),
                help_text=_('Your SSLCommerz Store ID'),
            )),
            ('store_passwd', forms.CharField(
                label=_('Store Password / API Secret Key'),
                widget=forms.PasswordInput(render_value=True),
                help_text=_('Your SSLCommerz Store Password'),
            )),
            ('sandbox', forms.BooleanField(
                label=_('Sandbox / Test Mode'),
                required=False,
                initial=True,
                help_text=_('Keep ON while testing. Turn OFF for live payments.'),
            )),
        ]
        return OrderedDict(list(super().settings_form_fields.items()) + fields)

    def is_allowed(self, request, total=None):
        return bool(
            self.settings.get('store_id') and
            self.settings.get('store_passwd')
        )

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request, **kwargs):
        return _('You will be redirected to SSLCommerz to complete your payment.')

    def payment_form_render(self, request, **kwargs):
        return _('You will be redirected to SSLCommerz to complete your payment.')

    def checkout_prepare(self, request, cart):
        return True

    def payment_prepare(self, request, payment):
        return True

    def execute_payment(self, request, payment):
        order = payment.order
        sandbox = self.settings.get('sandbox', as_type=bool)

        api_url = (
            'https://sandbox.sslcommerz.com/gwprocess/v4/api.php'
            if sandbox else
            'https://securepay.sslcommerz.com/gwprocess/v4/api.php'
        )

        url_kwargs = {
            'organizer': self.event.organizer.slug,
            'event': self.event.slug,
            'payment': payment.pk,
        }
        return_url = build_absolute_uri(
            self.event, 'plugins:pretix_sslcommerz:return', kwargs=url_kwargs
        )
        cancel_url = build_absolute_uri(
            self.event, 'plugins:pretix_sslcommerz:cancel', kwargs=url_kwargs
        )

        try:
            ia = order.invoice_address
            cus_name    = ia.name or 'Customer'
            cus_address = str(ia.street) if ia.street else 'N/A'
            cus_city    = str(ia.city) if ia.city else 'N/A'
            cus_phone   = str(ia.phone) if ia.phone else ''
        except Exception:
            cus_name    = 'Customer'
            cus_address = 'N/A'
            cus_city    = 'N/A'
            cus_phone   = ''

        payload = {
            'store_id':         self.settings.get('store_id'),
            'store_passwd':     self.settings.get('store_passwd'),
            'total_amount':     str(payment.amount),
            'currency':         self.event.currency,
            'tran_id':          f'{order.code}-{payment.pk}',
            'success_url':      return_url,
            'fail_url':         return_url,
            'cancel_url':       cancel_url,
            'cus_name':         cus_name,
            'cus_email':        order.email or 'noemail@example.com',
            'cus_phone':        cus_phone,
            'cus_add1':         cus_address,
            'cus_city':         cus_city,
            'cus_country':      'Bangladesh',
            'product_name':     str(self.event.name)[:50],
            'product_category': 'Tickets',
            'product_profile':  'general',
            'shipping_method':  'NO',
            'num_of_item':      '1',
        }

        try:
            response = requests.post(api_url, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            logger.error('SSLCommerz API timed out for payment %s', payment.pk)
            raise PaymentException(_('SSLCommerz did not respond in time. Please try again.'))
        except Exception as exc:
            logger.exception('SSLCommerz API error for payment %s: %s', payment.pk, exc)
            raise PaymentException(_('Could not connect to SSLCommerz. Please try again.'))

        if data.get('status') != 'SUCCESS':
            logger.error('SSLCommerz session error for payment %s: %s', payment.pk, data)
            raise PaymentException(
                _('SSLCommerz error: %s') % data.get('failedreason', 'Unknown error')
            )

        payment.info_data = {'sessionkey': data.get('sessionkey', '')}
        payment.save(update_fields=['info'])

        return str(data['GatewayPageURL'])

    def validate_payment_with_api(self, val_id, sandbox, payment_obj):
        """
        Double-verify payment via SSLCommerz Validation API.
        Strictly checks status, tran_id, amount AND currency.
        This prevents an attacker reusing a valid val_id from a
        cheap ticket to unlock an expensive one.
        """
        base_url = (
            'https://sandbox.sslcommerz.com'
            if sandbox else
            'https://securepay.sslcommerz.com'
        )
        validate_url = f'{base_url}/validator/api/validationserverAPI.php'

        params = {
            'val_id':       val_id,
            'store_id':     self.settings.get('store_id'),
            'store_passwd': self.settings.get('store_passwd'),
            'format':       'json',
        }

        try:
            response = requests.get(validate_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 1. Check status
            if data.get('status') not in ['VALID', 'VALIDATED']:
                logger.warning('SSLCommerz validation returned bad status: %s', data.get('status'))
                return False

            # 2. Check transaction ID matches this exact payment
            expected_tran_id = f'{payment_obj.order.code}-{payment_obj.pk}'
            if data.get('tran_id') != expected_tran_id:
                logger.error(
                    'SSLCommerz tran_id mismatch. Expected: %s Got: %s',
                    expected_tran_id, data.get('tran_id')
                )
                return False

            # 3. Check amount paid is not less than expected
            api_amount      = float(data.get('amount', 0))
            expected_amount = float(payment_obj.amount)
            if api_amount < expected_amount:
                logger.error(
                    'SSLCommerz amount mismatch. Expected: %s Got: %s',
                    expected_amount, api_amount
                )
                return False

            # 4. Check currency matches
            if data.get('currency') != self.event.currency:
                logger.error(
                    'SSLCommerz currency mismatch. Expected: %s Got: %s',
                    self.event.currency, data.get('currency')
                )
                return False

            return True

        except Exception as exc:
            logger.exception('SSLCommerz validation API error: %s', exc)
            return False

    def execute_refund(self, refund):
        raise NotImplementedError(
            'SSLCommerz refunds must be processed manually via the merchant dashboard.'
        )
