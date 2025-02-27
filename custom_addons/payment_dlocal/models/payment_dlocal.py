from odoo import models, fields
import requests
import json

class PaymentProviderDLocal(models.Model):
    _inherit = "payment.provider"

    # Agregar el código de selección "dlocal" a los métodos de pago
    code = fields.Selection(
        selection_add=[('dlocal', "dLocal")], ondelete={'dlocal': 'set default'}
    )
    
    # Agregar los campos necesarios para la integración con dLocal
    dlocal_api_key = fields.Char(string="API Key")
    dlocal_secret_key = fields.Char(string="Secret Key")
    dlocal_endpoint = fields.Char(string="API Endpoint", required=True)

    def get_api_credentials(self):
        """ Retrieve API credentials securely from Odoo configuration. """
        Param = self.env['ir.config_parameter'].sudo()
        return {
            'api_key': Param.get_param('dlocal.api_key', default=''),
            'secret_key': Param.get_param('dlocal.secret_key', default='')
        }

    def process_payment(self, values):
        """ Process payment with dLocal API """
        credentials = self.get_api_credentials()
        if not credentials['api_key']:
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
            "Authorization": f"Bearer {credentials['api_key']}"
        }

        try:
            # Realizar solicitud de pago
            response = requests.post(f"{self.dlocal_endpoint}/payments", headers=headers, json=data)
            response.raise_for_status()  # Lanza un error en caso de respuesta HTTP 4xx o 5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error in payment request to dLocal: {e}")
