# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


#Agrega al formulario los capos requeridos por el Sat
class AccountInvoiceLine(models.Model):
    _name = 'account.invoice.line'
    _inherit = ['account.invoice.line']

    no_identificacion = fields.Char(string='No Identificador')

    @api.onchange('product_id')
    def _onchange_product(self):
        self.no_identificacion = self.product_id.default_code;




    def _get_price_tax(self):
        for l in self:
            l.price_tax = l.price_total - l.price_subtotal

    price_tax = fields.Monetary(string='Tax Amount', compute='_get_price_tax', store=False)

