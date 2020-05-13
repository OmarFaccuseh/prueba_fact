# -*- coding: utf-8 -*-
{
    'name': "Sft-Facturacion | CFDI 3.3",

    'summary': """
        Modulo de timbrado de CFDI 3.3 hacia Sft-Facturacion""",
	'license': 'OPL-1',
    'description': """
        El modulo esta integrado al portal de Sft-Facturacion, heredando toda la funcionalidad tanto en el portal en linea, como en el modulo dentro de Odoo.
    """,

    'author': "Softhink",
    'website': "http://www.sft.com.mx",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1.4',

    # any module necessary for this one to work correctly
    'depends': ['sale','point_of_sale','stock','account','account_invoicing','account_cancel', 'vit_currency_inverse_rate','currency_rate_update'],
    #'depends': ['account','account_accountant'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views_account_invoice.xml',
        'views/views_product_template.xml',
        'views/views_res_partner.xml',
        'views/views_res_company.xml',

        'views/views_account_payment.xml',
        'views/views_wizard_account_invoice_refund.xml',
        #'views/view_sale_order.xml',
        'views/view_sat_pendiente_cancelar.xml',
        'data/parametros.xml',

        'views/views_c_aduanas.xml',
        'views/views_c_ClaveProdServicios.xml',
        'views/views_c_ClaveUnidad.xml',
        'views/views_Codigo_P.xml',
        'views/views_forma_de_pago.xml',
        'views/views_metodo_pago.xml',
        'views/views_impuestos.xml',
        'views/views_NumPedimentoAduana.xml',
        'views/views_c_paises.xml',
        'views/views_c_patente_aduanal.xml',
        'views/views_c_regimen_fiscal.xml',
        'views/views_c_tasa_cuota.xml',
        'views/views_c_tipo_factor.xml',
        'views/views_c_tipo_relacion.xml',
        'views/views_c_uso_cfdi.xml',
        'views/views_c_tipo_comprobante.xml',
        'views/views_c_configuracion.xml',
        'views/views_bancos.xml',
        #'Archivos_CSV/cfdi.configuracion.csv',
	'views/views_sft_ayuda_error_factura.xml',
    ]
    ,'demo': [

    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
	"images":['static/description/Integracion4.jpg'],
}
