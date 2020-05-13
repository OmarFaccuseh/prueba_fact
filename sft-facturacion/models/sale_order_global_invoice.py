# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import models, fields, api,_
import hashlib
import logging

class PedidoFacturaGlobal(models.Model):
    _name = 'sale.order.global_invoice'

    partner_id = fields.Many2one('res.partner',string='Cliente')
    date = fields.Datetime(string='Fecha')
    product_id = fields.Many2one('product.product',string='Producto')
