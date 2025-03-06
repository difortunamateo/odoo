import hashlib
import hmac
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
class DLocalController(http.Controller):

    @http.route('/payment/dlocal/checkout', type='http', auth='public', website=True)
    def dlocal_checkout(self, **post):
        """ Construye y redirige al formulario de pago de dLocal. """
        # Obtener la transacción basada en el ID de referencia
        tx_id = post.get('tx_id')
        tx = request.env['payment.transaction'].sudo().browse(int(tx_id))

        if not tx or tx.provider_code != 'dlocal':
            return request.redirect('/shop/payment')

        rendering_values = tx._get_specific_rendering_values({
            'amount': tx.amount,
            'currency_code': tx.currency_id.name,
            'reference': tx.reference,
        })

        return request.render(
            'payment_dlocal.redirect_form', rendering_values
        )

    @http.route('/payment/dlocal/return', type='http', auth='public', website=True, csrf=False)
    def dlocal_return(self, **post):
        """ Procesa la respuesta de dLocal después de un pago. """
        # Validar la respuesta
        reference = post.get('reference')
        if not reference:
            return request.redirect('/shop/payment')

        tx = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'dlocal', post
        )

        # Procesar el feedback
        tx._handle_feedback_data('dlocal', post)

        # Redirigir al usuario
        return request.redirect('/payment/status')

    @http.route('/payment/dlocal/webhook', type='json', auth='public', csrf=False)
    def dlocal_webhook(self):
        """ Maneja las notificaciones webhook de dLocal. """
        data = request.jsonrequest
        _logger.info("Recibida notificación webhook de dLocal: %s", data)

        # Validar la firma de la notificación
        if not self._validate_dlocal_signature(data):
            return {'status': 'error', 'message': 'Invalid signature'}

        # Procesar la notificación
        reference = data.get('order_id')
        tx = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'dlocal', data
        )

        if tx:
            tx._handle_feedback_data('dlocal', data)
            return {'status': 'ok'}

        return {'status': 'error', 'message': 'Transaction not found'}

    def _validate_dlocal_signature(self, data):
        """ Valida la firma de dLocal en las notificaciones. """
        provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'dlocal')], limit=1
        )

        if not provider:
            return False

        # Extraer los campos relevantes para la validación
        signature = data.get('signature')
        order_id = data.get('order_id')
        amount = data.get('amount')
        status = data.get('status')

        # Construir el mensaje para la firma
        msg = f"{provider.x_dlocal_api_key}{amount}{order_id}{status}"
        expected_signature = hmac.new(
            provider.x_dlocal_secret_key.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)