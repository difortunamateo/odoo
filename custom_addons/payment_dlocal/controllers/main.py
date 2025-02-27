from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class DLocalController(http.Controller):

    @http.route(['/payment/dlocal/notify'], type='json', auth='public', methods=['POST'], csrf=False)
    def dlocal_notify(self, **post):
        # Registra el contenido recibido para la notificación
        _logger.info("Received dLocal notification: %s", post)

        # Obtener los valores de referencia y estado
        reference = post.get('order_id')
        status = post.get('status')

        # Verificar si falta la referencia o el estado
        if not reference or not status:
            _logger.error("Missing reference or status in the notification: reference=%s, status=%s", reference, status)
            return {'status': 'error', 'message': 'Invalid notification data'}

        # Buscar la transacción correspondiente en el nuevo modelo
        transaction = request.env['payment.transaction.dlocal'].sudo().search([('dlocal_reference', '=', reference)], limit=1)

        if not transaction:
            _logger.error("Transaction not found for reference: %s", reference)
            return {'status': 'error', 'message': 'Transaction not found'}

        # Intentar actualizar el estado de la transacción
        try:
            _logger.info("Updating transaction status for reference: %s with status: %s", reference, status)
            transaction.update_status(status)
            _logger.info("Transaction status updated successfully for reference: %s", reference)
            return {'status': 'success'}
        except ValueError as e:
            # Capturar y registrar el error al intentar actualizar el estado
            _logger.error("Error updating transaction status for reference: %s. Error: %s", reference, str(e))
            return {'status': 'error', 'message': str(e)}