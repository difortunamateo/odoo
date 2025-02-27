{
    'name': 'dLocal Payment',
    'version': '1.0',
    'summary': 'Integración de pagos con dLocal en Odoo',
    'description': 'Permite a los clientes pagar con dLocal en el sitio web de Odoo.',
    'category': 'Accounting',
    'author': 'Tu Nombre',
    'depends': ['base', 'payment'],
    'data': [
        'views/payment_views.xml',
        'security/ir.model.access.csv',  
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
