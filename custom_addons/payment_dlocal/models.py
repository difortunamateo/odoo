import hashlib
import hmac
import logging

from werkzeug import urls

from odoo import models, fields
import requests
import json

_logger = logging.getLogger(__name__)

class PaymentProviderDLocal(models.Model):
    _inherit = "payment.provider"
    #_name = "payment.provider_dlocal"
    
    code = fields.Selection([('dlocal', 'dLocal')], required=True, default='dlocal')
    
    x_dlocal_api_key = fields.Char(string="API Key")
    x_dlocal_secret_key = fields.Char(string="Secret Key")
    x_dlocal_endpoint = fields.Char(string="API Endpoint", required=True, default="")

    def _make_dlocal_request(self, endpoint, payload=None, method='POST'):
        url = urls.url_join("https://api-sbx.dlocalgo.com/v1/payments", endpoint)
        headers = {'Authorization': f'Bearer oLQmkrFljJzfuOvykjZUJSdZgeAUfitK:ywIZqyuVngPnXtOaG6u58dzqgEvNB97BOV7HZAzD'}
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    _logger.exception(
                        "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload),
                    )
                    try:
                        response_content = response.json()
                        error_code = response_content.get('error')
                        error_message = response_content.get('message')
                        raise ValidationError("Dlocal: " + _(
                            "The communication with the API failed. Dlocal gave us the"
                            " following information: '%(error_message)s' (code %(error_code)s)",
                            error_message=error_message, error_code=error_code,
                        ))
                    except ValueError:  # The response can be empty when the access token is wrong.
                        raise ValidationError("Dlocal: " + _(
                            "The communication with the API failed. The response is empty. Please"
                            " verify your access token."
                        ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Dlocal: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.code != 'dlocal':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_dlocal.payment_method_dlocal').id

    def get_api_credentials(self):
        """ Retrieve API credentials securely from Odoo configuration. """
        Param = self.env['ir.config_parameter'].sudo()
        return {
            'dlocal_api_key': Param.get_param('dlocal.api_key', default=''),
            'dlocal_secret_key': Param.get_param('dlocal.secret_key', default='')
        }

    def process_payment(self, values):
        """ Process payment with dLocal API """
        _logger.info("Javi 2")
        credentials = self.get_api_credentials()
        if not credentials['dlocal_api_key']:
            raise ValueError("Missing dLocal API Key in system parameters.")

        # Validar campos requeridos
        required_fields = ['amount', 'currency', 'reference', 'partner_email', 'partner_name']
        missing_fields = [field for field in required_fields if field not in values]

        if missing_fields:
            raise ValueError(f"Missing required fields for payment: {', '.join(missing_fields)}")

        # Headers de la solicitud
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {credentials['dlocal_api_key']}:{credentials['dlocal_secret_key']}"
        }
                
        url = "https://api-sbx.dlocalgo.com/v1/payments"
        
        # Preparar datos de la solicitud
        data = {
            "amount": values['amount'],
            "currency": values['currency'],
            "order_id": values['reference'],
            "country": "UY",
            "description": f"Order {values['reference']} - example.com",
            "payment_method": "CARD",
            "payer": {
                "email": values['partner_email'],
                "name": values['partner_name']
            }
        }
        
        _logger.info(f"Data: {data}")

        try:
            #requests.headers = {'Content-type': 'application/json'}
            response = requests.post(url, headers=headers, json=data)
            _logger.error(f"Error response: {response.text}")
            response.raise_for_status()  # Lanza un error en caso de respuesta HTTP 4xx o 5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error in payment request to dLocal: {e}")
        
    def _dlocal_get_inline_form_values(self, currency=None):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param res.currency currency: The transaction currency.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        inline_form_values = {
            'provider_id': self.id,
            'api_key': self.x_dlocal_api_key,
            'currency_code': currency and currency.name,
        }
        return json.dumps(inline_form_values)

class PaymentTransactionDLocal(models.Model):
    _inherit = "payment.transaction"

    # Campos específicos de DLocal
    x_dlocal_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
    ], string="dLocal Status", default='pending')

    x_dlocal_reference = fields.Char(string="dLocal Reference")
    x_dlocal_payment_method = fields.Char(string="Payment Method")

    def update_status(self, status):
        """ Actualizar el estado de la transacción de acuerdo con el estado recibido desde DLocal. """
        if status not in dict(self._fields['dlocal_status'].selection):
            raise ValueError(f"Invalid status: {status}")

        self.dlocal_status = status

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'dlocal':
            return res

        # No se si acá no hay que cambiar para que no sea localhost, probarlo.
        #base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url = 'https://e8b0-2800-ac-8014-f673-f9b9-fe43-75fc-1a61.ngrok-free.app'

        tx_values = {
            'currency': self.currency_id.name,
            'amount': processing_values['amount'],
            'country': self.partner_country_id.code,
            'order_id': self.reference,
            'description': self.reference + ' - ' + self.partner_name,
            'success_url': urls.url_join(base_url, '/payment/dlocal/success'),
            'back_url': urls.url_join(base_url, '/payment/dlocal/return'),
            'notification_url': urls.url_join(base_url, '/payment/dlocal/notifications'),
        }

        #Firmamos
        msg = f"{self.provider_id.x_dlocal_secret_key}{tx_values['amount']}{tx_values['order_id']}"
        tx_values['signature'] = hmac.new(
            self.provider_id.x_dlocal_secret_key.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()


        api_url = f"{self.provider_id.x_dlocal_endpoint}/v1/payments"
        #api_url = "https://api-sbx.dlocalgo.com/v1/payments"
    
        return {
            'api_url': api_url,
            'tx_values': tx_values,
        }

    def _get_tx_from_feedback_data(self, provider_code, data):

        tx = super()._get_tx_from_feedback_data(provider_code, data)
        if provider_code != 'dlocal' or tx:
            return tx

        reference = data.get('order_id') or data.get('reference')
        if not reference:
            return False

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'dlocal')])
        return tx

    def _process_feedback_data(self, data):

        super()._process_feedback_data(data)
        if self.provider_code != 'dlocal':
            return

        status = data.get('status')
        tx_id = data.get('payment_id')

        # Actualizar datos de la transacción
        vals = {
            'x_dlocal_reference': tx_id,
            'x_dlocal_status': self._dlocal_map_status(status),
            'x_dlocal_payment_method': data.get('payment_method_type', ''),
            'provider_reference': tx_id,
        }

        self.write(vals)

        # Actualizar el estado de la transacción en Odoo
        if status == 'PAID' or status == 'AUTHORIZED':
            self._set_done()
        elif status == 'PENDING' or status == 'VERIFICATION':
            self._set_pending()
        elif status == 'REJECTED' or status == 'CANCELLED':
            self._set_canceled()
        else:
            self._set_error("dLocal: " + data.get('status_detail', 'Unknown error'))

    def _dlocal_map_status(self, status):
        """ Mapper dlocal interno nuestro. """
        mapping = {
            'PAID': 'approved',
            'AUTHORIZED': 'approved',
            'PENDING': 'pending',
            'VERIFICATION': 'pending',
            'REJECTED': 'rejected',
            'CANCELLED': 'rejected',
            'ERROR': 'failed',
        }
        return mapping.get(status, 'pending')
