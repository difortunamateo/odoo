from odoo import models, fields
import requests
import json

class PaymentProviderDLocal(models.Model):
    _inherit = "payment.provider"
    #_name = "payment.provider_dlocal"
    
    code = fields.Selection([('dlocal', 'dLocal')], required=True, default='dlocal')
    
    x_dlocal_api_key = fields.Char(string="API Key")
    x_dlocal_secret_key = fields.Char(string="Secret Key")
    x_dlocal_endpoint = fields.Char(string="API Endpoint", required=True, default="")
    
    def get_api_credentials(self):
        """ Retrieve API credentials securely from Odoo configuration. """
        Param = self.env['ir.config_parameter'].sudo()
        return {
            'dlocal_api_key': Param.get_param('dlocal.api_key', default=''),
            'dlocal_secret_key': Param.get_param('dlocal.secret_key', default='')
        }

    def process_payment(self, values):
        """ Process payment with dLocal API """
        credentials = self.get_api_credentials()
        if not credentials['dlocal_api_key']:
            raise ValueError("Missing dLocal API Key in system parameters.")

        # Validar campos requeridos
        required_fields = ['amount', 'currency', 'reference', 'partner_email', 'partner_name']
        missing_fields = [field for field in required_fields if field not in values]

        if missing_fields:
            raise ValueError(f"Missing required fields for payment: {', '.join(missing_fields)}")

        # Preparar datos de la solicitud
        data = {
            "amount": values['amount'],
            "currency": values['currency'],
            "order_id": values['reference'],
            "payment_method": "CARD",
            "payer": {
                "email": values['partner_email'],
                "name": values['partner_name']
            }
        }

        # Cabeceras de la solicitud
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials['dlocal_api_key']}"
        }

        try:
            # Realizar solicitud de pago
            response = requests.post(f"{self.dlocal_endpoint}/payments", headers=headers, json=data)
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
    _inherit = "payment.transaction"  # Extiende el modelo de transacciones estándar
    #_name = "payment.transaction_dlocal"  # Reemplaza el nombre del modelo

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

        # Initiate the payment and retrieve the payment link data.
        #payload = self._dlocal_prepare_preference_request_payload()
        #_logger.info(
        ##    "Sending '/checkout/preferences' request for link creation:\n%s",
        #    pprint.pformat(payload),
        #)
        #api_url = self.provider_id._mercado_pago_make_request(
        #    '/checkout/preferences', payload=payload
        #)['init_point' if self.provider_id.state == 'enabled' else 'sandbox_init_point']

        # Extract the payment link URL and params and embed them in the redirect form.
        #parsed_url = urls.url_parse(api_url)
        #url_params = urls.url_decode(parsed_url.query)
        api_url = "https://api-sbx.dlocalgo.com/v1/payments"
        rendering_values = {
            'api_url': api_url,
            # 'url_params': url_params,  # Encore the params as inputs to preserve them.
        }
        return rendering_values
    
    def _dlocal_prepare_preference_request_payload(self):
        base_url = self.provider_id.get_base_url()
        return_url = urls.url_join(base_url, MercadoPagoController._return_url)
        sanitized_reference = url_quote(self.reference)
        webhook_url = urls.url_join(
            base_url, f'{MercadoPagoController._webhook_url}/{sanitized_reference}'
        )  # Append the reference to identify the transaction from the webhook notification data.

        unit_price = self.amount
        decimal_places = const.CURRENCY_DECIMALS.get(self.currency_id.name)
        if decimal_places is not None:
            unit_price = float_round(unit_price, decimal_places, rounding_method='DOWN')

        return {
            'auto_return': 'all',
            'back_urls': {
                'success': return_url,
                'pending': return_url,
                'failure': return_url,
            },
            'external_reference': self.reference,
            'items': [{
                'title': self.reference,
                'quantity': 1,
                'currency_id': self.currency_id.name,
                'unit_price': unit_price,
            }],
            'notification_url': webhook_url,
            'payer': {
                'name': self.partner_name,
                'email': self.partner_email,
                'phone': {
                    'number': self.partner_phone,
                },
                'address': {
                    'zip_code': self.partner_zip,
                    'street_name': self.partner_address,
                },
            },
            'payment_methods': {
                'installments': 1,  # Prevent MP from proposing several installments for a payment.
            },
        }
