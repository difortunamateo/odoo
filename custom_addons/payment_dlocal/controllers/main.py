from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class DLocalController(http.Controller):

    @http.route(['/payment/dlocal/notify'], type='json', auth='public', methods=['POST'], csrf=False)
    def dlocal_notify(self, **post):
        _logger.info("Received dLocal notification: %s", post)

        reference = post.get('order_id')
        status = post.get('status')

        if not reference or not status:
            return {'status': 'error', 'message': 'Invalid notification data'}

        transaction = request.env['payment.transaction.dlocal'].sudo().search([('reference', '=', reference)], limit=1)

        if not transaction:
            return {'status': 'error', 'message': 'Transaction not found'}

        try:
            transaction.update_status(status)
            return {'status': 'success'}
        except ValueError as e:
            _logger.error("Error updating transaction: %s", str(e))
            return {'status': 'error', 'message': str(e)}
