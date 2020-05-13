# -*- coding: utf-8 -*-
import re
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import api, fields, models

class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = 'pos.order'

    # TODO ADD OMAR
    cfdi_id = fields.Many2one('cfdi.uso_cfdi')
    metodo_id = fields.Many2one('cfdi.metodo_cfdi')
    forma_id = fields.Many2one('cfdi.forma_cfdi')

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)

        order_fields['cfdi_id'] = ui_order.get('cfdi_id', False)
        order_fields['metodo_id'] = ui_order.get('metodo_id', False)
        order_fields['forma_id'] = ui_order.get('forma_id', False)

        return order_fields
    # fin

    @api.multi
    def action_pos_order_invoice(self):
        codigo_search = self.env['cfdi.codigo_postal'].search([('c_codigopostal', '=', self.env.user.company_id.zip)])
        # if codigo_search.id== False:
        #    raise ValidationError("Compruebe el Codigo Postal colocado en la configuracion de la compania ya que no se encuentra en el catalogo del sat")

        # if self.env.user.company_id.state_id.name == False:
        #     raise ValidationError("La Compañia no tiene asignado ningun Estado")

        referencia = self.name;

        res = super(PosOrder, self).action_pos_order_invoice();
        invoice = self.env['account.invoice'].browse(res['res_id'])

        # TODO EDIT BY OMAR ors y forma_pago
        valores = {"metodo_pago_id": self.metodo_id.id or self.partner_id.metodo_pago_id.id,
                   "uso_cfdi_id": self.cfdi_id.id or self.partner_id.uso_cfdi_id.id,
                   'forma_pago_id': self.forma_id.id,
                   'compania_estado': self.env.user.company_id.state_id.name,
                   'rfc_cliente_factura': (self.partner_id.vat or self.partner_id.nif).encode('utf-8'),
                   'rfc_emisor': (self.env.user.company_id.company_registry).encode('utf-8'),
                   'compania_calle': (self.env.user.company_id.street).encode('utf-8'),
                   'compania_ciudad': (self.env.user.company_id.city).encode('utf-8'),
                   'compania_pais': (self.env.user.company_id.country_id.name).encode('utf-8'),
                   'observaciones': ("REFERENCIA: " + referencia).encode('utf-8')
                   }

        invoice.write(valores)

        return res