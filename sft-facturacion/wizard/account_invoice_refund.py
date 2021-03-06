# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _name = "account.invoice.refund"
    _description = "Invoice Refund"

    @api.model
    def _get_reason(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.name
        return ''

    date_invoice = fields.Date(string='Refund Date', default=fields.Date.context_today, required=True)
    date = fields.Date(string='Accounting Date')
    tipo_de_relacion_id = fields.Many2one('cfdi.tipo_relacion',string='Tipo de Relacion')
    description = fields.Char(string='Reason', required=True, default=_get_reason)
    refund_only = fields.Boolean(string='Technical field to hide filter_refund in case invoice is partially paid', compute='_get_refund_only')
    filter_refund = fields.Selection([('refund', 'Create a draft refund'), ('cancel', 'Cancel: create refund and reconcile'), ('modify', 'Modify: create refund, reconcile and create a new draft invoice')],
        default='refund', string='Refund Method', required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled')

    nota_credito_total = fields.Float(string="Monto nota de crédito");


    factura_origen = fields.Char()  # cuando es la nota es generada desde pos


    @api.constrains('nota_credito_total')
    def valida_monto(self):
        print("valida_monto")
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id',False))
        print(invoice_id.amount_total)
        print(self.nota_credito_total)
        if invoice_id.amount_total < self.nota_credito_total and invoice_id:
            raise ValidationError("Error de Validacion : El monto máximo a acreditar es de %s" % (str(invoice_id.amount_total)) )




    @api.depends('date_invoice')
    @api.one
    def _get_refund_only(self):
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id',False))
        if len(invoice_id.payment_move_line_ids) != 0 and invoice_id.state != 'paid':
            self.refund_only = True
        else:
            self.refund_only = False


    @api.multi
    def compute_refund(self, mode='refund'):  #todo omar add params id_fact_orig monto_nota_cr  : cancelar factura de ticket desde pos
        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False

            for inv in inv_obj.browse(int(form.factura_origen) or context.get('active_ids')):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise UserError(_('Cannot refund draft/proforma/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot refund invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id)

                # todo add by omar
                lineas_objs = self.env['account.invoice.line'].browse(refund.invoice_line_ids.ids)
                lineas_objs.write({'price_unit': self.nota_credito_total})

                # actualiza impuestos
                refund.write({'amount_tax': lineas_objs.price_tax, 'amount_total': lineas_objs.price_total})
                refund._onchange_invoice_line_ids()
                refund._compute_amount()


                refund.cfdi_relacionados = inv.uuid
                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    # campos en los que la informacion que aparece en la factura retrictiva(Nota de Credito) esta en False
                    # Aqui se setean los campos faltas desde el objeto inv(Factura Original)
                    if inv.tipo_de_relacion_id.id == False:
                        inv.tipo_de_relacion_id = self.tipo_de_relacion_id.id
                    refund.rfc_cliente_factura = inv.rfc_cliente_factura
                    refund.fac_id = inv.fac_id
                    refund.tipo_de_relacion_id= inv.tipo_de_relacion_id.id
                    refund.forma_pago_id = inv.forma_pago_id
                    refund.metodo_pago_id = inv.metodo_pago_id
                    refund.uso_cfdi_id = inv.uso_cfdi_id
                    refund.action_invoice_open()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                            to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                        })
                        for field in inv_obj._get_refund_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_refund = inv_obj.create(invoice)
                        if inv_refund.payment_term_id.id:
                            inv_refund._onchange_payment_term_date_invoice()
                        created_inv.append(inv_refund.id)
                xml_id = (inv.type in ['out_refund', 'out_invoice']) and 'action_invoice_tree1' or \
                         (inv.type in ['in_refund', 'in_invoice']) and 'action_invoice_tree2'
                # Put the reason in the chatter
                subject = _("Invoice refund")
                body = description
                refund.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            invoice_domain = safe_eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True





    @api.multi
    def invoice_refund(self):  #todo omar add params id_fact_orig monto_nota_cr  : cancelar factura de ticket desde pos
        if self.filter_refund == 'cancel':
            if self.tipo_de_relacion_id.id == False:
                raise ValidationError("No ha ingresado El Tipo de Relacion Para la Nota de Credito")
        data_refund = self.read(['filter_refund'])[0]['filter_refund']

        averquehay = self.compute_refund(data_refund)

        #last_id = self.env['account.invoice'].search([])[-1].id

        #nota_creada = self.env['account.invoice'].browse(last_id)

        averquehay['view_id'] = self.env.ref('account.invoice_tree').id
        #averquehay['view_type'] = 'tree'
        #averquehay['res_id'] = averquehay['domain'][1][2][0]  # accede al id de la nota
        #averquehay['views'] = [[False, 'tree']]
        averquehay['domain'] =  [('type','=','out_refund')]

        #averquehay['target'] = 'inline'



        return averquehay

    @api.multi
    def set_invoice_for_nota(self, factura_id):
        self.factura_origen = factura_id