{
    'name': 'dLocal Payment',
    'version': '1.0',
    'summary': 'Integración de pagos con dLocal en Odoo',
    'description': 'Permite a los clientes pagar con dLocal en el sitio web de Odoo.',
    'category': 'Accounting',
    'author': 'Mateo Di Fortuna',
    'depends': ['base', 'payment'],
    'data': [
        #'views/payment_provider_form_dlocal.xml',
        #'views/payment_dlocal_method_form.xml',
        #'views/payment_transaction_form_dlocal.xml',
        #'security/ir.model.access.csv',  
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
