    # -*- coding: utf-8 -*-
from decimal import Decimal
import pytz
import datetime
import re
import time
import json
import hashlib
import requests
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from dateutil.tz import tzlocal
from odoo import api, fields, models

import logging
from odoo import models, fields, api,_
import math

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = 'account.payment'

    _logger = logging.getLogger(__name__)

    documentos_relacionados = fields.One2many('account.payment.docto', 'payment_id', string="Factura")

    #TODO add omar
    @api.depends('partner_type')
    def computeEsProveedor(self):
        for record in self:
            if record.partner_type == 'Proveedor' or record.partner_type == 'supplier' or record.partner_type == 'Vendor':
                record.es_proveedor = True
            else:
                record.es_proveedor = False
    es_proveedor = fields.Boolean(string='True si es un pago a proveedor', compute='computeEsProveedor', store=True)


    @api.model
    def default_get(self, fields):
        modelo = super(AccountPayment, self);
        rec = modelo.default_get(fields)
        # rec = super(AccountPayment, self).default_get(fields)
        # self.imp_saldo_ant = self.invoice_ids.residual;
        context = dict(self._context or {})
        active_model = context.get('active_model')

        active_ids = context.get('active_ids')
        if active_model != None and "account.invoice" in active_model:
            invoices = self.env[active_model].browse(active_ids)
            saldo_anterior = 0.0;
            moneda = None;
            for invoice in invoices:
                saldo_anterior = saldo_anterior + invoice.residual;
                moneda = invoice.currency_id.name;

            # rec['imp_saldo_ant'] = saldo_anterior;
            # rec['moneda_factura'] = moneda;
        return rec

    # @api.model
    # def create(self, vals):
    #     return super(AccountPayment, self).create(vals)

    @api.one
    def compute_default(self):
        for pago in self:
            if pago.invoice_ids != None and pago.invoice_ids != False:
                # pago.imp_saldo_ant = pago.invoice_ids.residual;
                pago.imp_saldo_ant = 0;
                for invoice in pago.invoice_ids:
                    pago.imp_saldo_ant = pago.imp_saldo_ant + invoice.residual;

                if hasattr(pago.invoice_ids,
                           "invoices") and pago.invoice_ids.invoices != None and pago.invoice_ids.invoices != False \
                        and pago.invoice_ids.invoices != None and pago.invoice_ids.invoices.currency_id != None:
                    pago.moneda_factura = pago.invoice_ids.invoices.currency_id.name;

    id_banco_seleccionado= fields.Integer('id_banco_seleccionado')
    formadepagop_id = fields.Many2one('cfdi.forma_pago',string='Forma de pago')
    moneda_p = fields.Many2one('res.currency', string='Moneda',
                               default=lambda self: self.env.user.company_id.currency_id)
    # moneda_factura = fields.Char(string='Moneda Factura', store=False)
    tipocambiop = fields.Float('Tipo de cambio a MXN', readonly=True, compute='_computeTC')
    # tipocambio_oper = fields.Char('Tipo de operacion')
    uuid = fields.Char(string="UUID",readonly=True)
    # no_parcialidad = fields.Char(string='No. Parcialidad')
    # imp_saldo_ant = fields.Monetary('Importe Saldo Anterior', default=lambda self: self.invoice_ids.residual)
    # imp_saldo_ant = fields.Monetary('Importe Saldo Anterior')
    # imp_saldo_insoluto = fields.Monetary('Importe Saldo Insoluto')
    timbrada = fields.Char('CFDI', default="Sin Timbrar", readonly=True)
    fac_id = fields.Char()
    pdf = "Factura?Accion=descargaPDF&fac_id=";
    xml = "Factura?Accion=ObtenerXML&fac_id=";

    amount = fields.Monetary(string='Payment Amount', stored="True")
    amount_otro = fields.Monetary(string='Payment Amount',  stored=False, readonly=True)

    calculo = fields.Char("calculo", store=True, compute='compute_default')

    def establecer_uso_de_cfdi(self):
        uso = self.env['cfdi.uso_cfdi'].search([('id', '=', '22')])
        return uso

    uso_cfdi_id = fields.Many2one('cfdi.uso_cfdi',string='Uso CFDI',default=establecer_uso_de_cfdi)

    # @api.one
    def establecer_referencia_de_pago(self):
        ref = "";
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')
        if active_model != None and "account.invoice" in active_model:
            invoices = self.env['account.invoice'].browse(self._context.get('active_ids'))
            for invoice in invoices:
                if len(ref) > 0:
                    ref = ref + ",";
                ref = invoice.number
                # self.communication = ksks
                return ref


    #todo add omar - cliente
    @api.onchange('cta_ordenante')
    def onchangeCuentaCliente(self):
        self.nom_banco_ord_ext_id = self.cta_ordenante.banco.id
        self.rfc_emisor_cta_ord = self.cta_ordenante.banco.rfc_banco

    @api.multi
    @api.onchange('partner_id')
    def set_cuentas_cliente_domain(self):
        for record in self:

            # maybe this no deveria no deberia ser cambiado
            if not self.cta_beneficiario:
                self.cta_beneficiario = self.journal_id.bank_acc_number
                self.rfc_emisor_cta_ben = self.journal_id.rfc_institucion_bancaria


            if self.cuentas_cliente:
                self.cta_ordenante = self.cuentas_cliente[0]

            res = "[('partner_id','=', " + str(self.partner_id.id) + ")]"

            record.env['ir.config_parameter'].sudo().set_param('domain_cuenta_clie', res)
            return {
                'domain': {'cta_ordenante': self.env['ir.config_parameter'].sudo().get_param('domain_cuenta_clie')}
            }

    no_operacion = fields.Char('No. de operacion',
                               help='Se puede registrar el número de cheque, número de autorización, '
                                    + 'número de referencia,\n clave de rastreo en caso de ser SPEI, línea de captura o algún número de referencia \n o '
                                    + 'identificaciín análogo que permita identificar la operación correspondiente al pago efectuado.',
                               required=True)

    @api.onchange('cuentas_cliente')
    def set_cuenta(self):
        if self.cuentas_cliente:
            self.cta_ordenante = self.cuentas_cliente[0]


    def defult_cuenta_cliente(self):
        if self.cuentas_cliente:
            return self.cuentas_cliente[0]
        else:
            return False


    cuentas_cliente = fields.One2many('cuenta.bancaria.sft', related='partner_id.mis_cuentas')

    rfc_emisor_cta_ord = fields.Char('RFC Emisor Institucion Bancaria')
    nom_banco_ord_ext_id = fields.Many2one('cfdi.bancos',string='Banco emisor')
    cta_ordenante = fields.Many2one('cuenta.bancaria.sft', string='Cuenta Ordenante', default=defult_cuenta_cliente) #todo omar cambio de char a modelo cuenta.sft
    rfc_emisor_cta_ben = fields.Char(string='RFC Emisor Cuenta Beneficiario', store=True, readonly=True) # todo omar add default
    cta_beneficiario = fields.Char(string='Cuenta Beneficiario', store=True, readonly=True)  #todo omar cambio de char a modelo cuenta.sft ->> revertido a CHAR)
    parcial_pagado = fields.Char(string='No. Parcialidad')
    ref = fields.Char(string='Referencia Factura', default=establecer_referencia_de_pago)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),
                              ('cancelled', 'Cancelled'), ('replaced', 'Reemplazado')],
                             readonly=True, default='draft', copy=False, string="Status")

    # state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'), ('cancelled', 'Cancelado'), ('replaced', 'Reemplazado')],
    #                         readonly=True, default='draft', copy=False, string="Status")

    @api.one
    @api.depends('communication')
    def Timbrara_Pago(self):
        self.timbrar_pago = True;
        return self.timbrar_pago;

        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')
        if active_model != None and "account.invoice" in active_model:
            invoice = self.env['account.invoice'].browse(self._context.get('active_ids'))
            for record in invoice:
                if record.fac_timbrada == 'Timbrada':
                    self.timbrar_pago = True
                else:
                    self.timbrar_pago = False
            return self.timbrar_pago

    timbrar_pago = fields.Boolean(string='Timbrar Factura', store=True, compute=Timbrara_Pago)

    ocultar = fields.Boolean(string='Meeeen', store=True, compute="_compute_ocultar", track_visibility='onchange')

    sustituye_pago = fields.Boolean(string='¿Este pago sustituye otro?', default=False,
                                    help='Se utiliza para cuando el pago en cuestión, va a sustituir algún pago que ya fué cancelado')
    pago_sustituye = fields.Many2one('account.payment', string='Pago a sustituir',
                                     help='Referencia con el pago que se va a sustituir')

    @api.one
    def _obtPuede_Cancelar(self):
        if self.state == 'posted' and self.timbrada == 'Sin Timbrar':
            self.puede_cancelar = True;
            return True;

        self.puede_cancelar = False;
        return False;

    puede_cancelar = fields.Boolean(string='Puede Cancelar', store=False, compute=_obtPuede_Cancelar)

    @api.one
    def _obtPuede_Editar(self):
        for pago in self:
            if pago.timbrada != False and 'Sin Timbrar' in pago.timbrada:
                pago.puede_editar = True;
                # return True;
            else:
                pago.puede_editar = False;
                # return False;

    puede_editar = fields.Boolean(string='Puede Editar', store=False, compute=_obtPuede_Editar, default=True)

    @api.onchange('currency_id')
    def _onchange_actualiza_tipo_cambio(self):
        self.documentos_relacionados._computeDocumento();

    @api.one
    @api.depends('formadepagop_id.c_forma_pago')
    def _compute_ocultar(self):
        if self.formadepagop_id.c_forma_pago == "01":
            self.ocultar = True
        else:
            self.ocultar = False

    @api.onchange('nom_banco_ord_ext_id')
    def _onchange_establecer_banco_emisor(self):
        for pago in self:
            pago.rfc_emisor_cta_ord = pago.nom_banco_ord_ext_id.rfc_banco
            pago.id_banco_seleccionado = pago.nom_banco_ord_ext_id.id

    @api.multi
    @api.onchange('journal_id', 'currency_id')
    def _onchange_actualiza_datos_bancarios(self):
        for record in self:
            None;
            record._calculaTipoCambio();
            # self.GuardaGeneralesPago(record);

    # @api.multi
    # @api.onchange('amount')
    # def _onchange_actualiza_amount(self):
    #     for record in self:
    #         None;
    #         #self.GuardaGeneralesPago(record);

    # @api.multi
    # @api.onchange('tipocambiop')
    # def _onchangeTipoCambioP(self):
    #     for record in self:
    #         self.GuardaGeneralesPago(record);

    # @api.multi
    # @api.onchange('tipocambio_oper')
    # def _onchangeTipoCambioOper(self):
    #     if "MXN" == self.invoice_ids.currency_id.name:
    #         self.tipocambiop = self.tipocambio_oper
    #     for record in self:
    #         self.GuardaGeneralesPago(record);

    @api.one
    def _computeTC(self):
        for record in self:
            record._calculaTipoCambio();

    def _calculaTipoCambio(self):
        for record in self:
            model_currency = self.env['res.currency'];
            # record.tipocambio_oper = record.currency_id.round(model_currency.with_context(date=record.payment_date)._get_conversion_rate(record.currency_id, record.invoice_ids.currency_id))

            currency_pesos = model_currency.search([('name', '=', 'MXN')])
            if currency_pesos == None or len(currency_pesos) == 0:
                record.tipocambiop = 1;
            else:
                record.tipocambiop = currency_pesos[0].round(
                    1 / model_currency.with_context(date=record.payment_date)._get_conversion_rate(currency_pesos[0],
                                                                                                   record.currency_id))

    # def _compute_total_invoices_amount(self):
    #     print("_compute_total_invoices_amount")
    #     """ Compute the sum of the residual of invoices, expressed in the payment currency """
    #     if self.tipocambio_oper!= None and self.tipocambio_oper != False:
    #         payment_currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id or self.env.user.company_id.currency_id
    #         invoices = self._get_invoices()
    #
    #         if all(inv.currency_id == payment_currency for inv in invoices):
    #             total = sum(invoices.mapped('residual_signed'))
    #         else:
    #             total = 0
    #             for inv in invoices:
    #                 if inv.company_currency_id != payment_currency:
    #                     total += inv.company_currency_id.with_context(date=self.payment_date).compute(inv.residual_company_signed, payment_currency)
    #                 else:
    #                     total += inv.residual_company_signed
    #         return abs(total)
    #     else:
    #         payment_currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id or self.env.user.company_id.currency_id
    #         invoices = self._get_invoices()
    #
    #         if all(inv.currency_id == payment_currency for inv in invoices):
    #             total = sum(invoices.mapped('residual_signed'))
    #         else:
    #             total = 0
    #             for inv in invoices:
    #                 if inv.company_currency_id != payment_currency:
    #                     total += inv.company_currency_id.with_context(date=self.payment_date).compute(inv.residual_company_signed, payment_currency)
    #                 else:
    #                     total += inv.residual_company_signed
    #         return abs(total)

    @api.one
    # @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id', 'tipocambio_oper')
    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id')
    def _compute_payment_difference(self):
        # print("_compute_payment_difference")
        self.calcula_montos(self.amount)
        if len(self.invoice_ids) == 0:
            return
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
            self.payment_difference = self.amount - self._compute_total_invoices_amount()
        else:
            self.payment_difference = self._compute_total_invoices_amount() - self.amount

    # @api.model
    # def compute_amount_fields(self, amount, src_currency, company_currency, invoice_currency=False):
    #     """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
    #     amount_currency = False
    #     currency_id = False
    #     if src_currency and src_currency != company_currency:
    #         amount_currency = amount
    #         amount = src_currency.with_context(self._context).compute(amount, company_currency)
    #         currency_id = src_currency.id
    #     debit = amount > 0 and amount or 0.0
    #     credit = amount < 0 and -amount or 0.0
    #     if invoice_currency and invoice_currency != company_currency and not amount_currency:
    #         amount_currency = src_currency.with_context(self._context).compute(amount, invoice_currency)
    #         currency_id = invoice_currency.id
    #     return debit, credit, amount_currency, currency_id

    # def calcula_montos(self, amount, src_currency, company_currency, invoice_currency=False):
    def calcula_montos(self, amount):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        amount_currency = amount
        # amount = amount_currency * self.tipocambio_oper;
        # amount = (Decimal(amount_currency))* (Decimal(self.tipocambio_oper));

        debit = amount > Decimal(0) and amount or Decimal(0.0)
        credit = amount < Decimal(0) and -Decimal(amount) or 0.0
        return debit, credit, Decimal(amount)
    #
    # @api.one
    # @api.depends('documentos_relacionados', 'documentos_relacionados.importe_pagado_moneda',
    #              'documentos_relacionados.tipocambio_dr', 'currency_id')
    # def _calculaTotal(self):
    #     for pago in self:
    #         sumatoria = 0;
    #         for linea in pago.documentos_relacionados:
    #             linea._computeDocumento();
    #
    #             sumatoria = sumatoria + linea.importe_pagado_moneda;
    #
    #         pago.amount = sumatoria;
    #         pago.amount_otro = pago.amount;
    #         return pago.amount;

    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            #Valida si el total a pagar sea mayor a lo de las lineas
            suma = 0.0;
            for documento in rec.documentos_relacionados:
                #Valida que los documentos tengan importe a facturar
                if documento.importe_pagado_moneda == False or documento.importe_pagado_moneda == None or documento.importe_pagado_moneda <= 0:
                    raise ValidationError("La factura %s no tiene importe a pagar "%str(documento.invoice_id.number))

                suma = suma + documento.importe_pagado_moneda;

            if suma > rec.amount:
                raise ValidationError(_("El importe a pagar (%s), es menor a las lineas de pago (%s)"%(rec.amount, suma)))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
                sequence_code)
            if not rec.name and rec.payment_type != 'transfer':
                raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

                # todo add omar - el puro if y todo el else
                if rec.documentos_relacionados:

                    # Create the journal entry
                    for documento in rec.documentos_relacionados:
                        amount = documento.importe_pagado * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                        move = rec._create_payment_entry(amount, documento.invoice_id)

                        # In case of a transfer, the first journal entry created debited the source liquidity account and credited
                        # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
                        if rec.payment_type == 'transfer':
                            transfer_credit_aml = move.line_ids.filtered(
                                lambda r: r.account_id == rec.company_id.transfer_account_id)
                            transfer_debit_aml = rec._create_transfer_entry(amount)
                            (transfer_credit_aml + transfer_debit_aml).reconcile()

                        rec.write({'state': 'posted', 'move_name': move.name})

                        # si la factura estÃ¡ saldada, la coloca como pagada
                        if documento.invoice_id.residual == 0:
                            print(".............Coloca como pagado")
                            documento.invoice_id.write({"state": 'paid'});
                else:
                    # todo omar - codigo original que "valida" pago
                    amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                    move = rec._create_payment_entry(amount, False)
                    persist_move_name = move.name

                    # In case of a transfer, the first journal entry created debited the source liquidity account and credited
                    # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
                    if rec.payment_type == 'transfer':
                        transfer_credit_aml = move.line_ids.filtered(
                            lambda r: r.account_id == rec.company_id.transfer_account_id)
                        transfer_debit_aml = rec._create_transfer_entry(amount)
                        (transfer_credit_aml + transfer_debit_aml).reconcile()
                        persist_move_name += self._get_move_name_transfer_separator() + transfer_debit_aml.move_id.name

                    rec.write({'state': 'posted', 'move_name': persist_move_name})
            return True

    def _create_payment_entry(self, amount, invoice):
        # if (self.payment_type == 'outbound'):
        if self.payment_type == 'outbound' or not invoice:
            return super(AccountPayment, self)._create_payment_entry(amount);

        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """

        # Coloca las facturas asignadas a las lineas
        arr_facturas = [];
        for documento in self.documentos_relacionados:
            arr_facturas.append(documento.invoice_id.id);

        self.invoice_ids = arr_facturas;

        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == invoice.currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = invoice.currency_id
        # debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id, invoice_currency)
        debit, credit, amount_currency = self.calcula_montos(amount)
        currency_id = invoice.currency_id.id;

        move = self.env['account.move'].create(self._get_move_vals())

        # Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(invoice))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(
                self.payment_difference, self.currency_id, self.company_id.currency_id, invoice_currency)[2:]
            # the writeoff debit and credit must be computed from the invoice residual in company currency
            # minus the payment amount in company currency, and not from the payment difference in the payment currency
            # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
            total_residual_company_signed = sum(invoice.residual_company_signed for invoice in self.invoice_ids)
            total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(self.amount,
                                                                                                         self.company_id.currency_id)
            if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
                amount_wo = total_payment_company_signed - total_residual_company_signed
            else:
                amount_wo = total_residual_company_signed - total_payment_company_signed
            # Align the sign of the secondary currency writeoff amount with the sign of the writeoff
            # amount in the company currency
            if amount_wo > 0:
                debit_wo = amount_wo
                credit_wo = 0.0
                amount_currency_wo = abs(amount_currency_wo)
            else:
                debit_wo = 0.0
                credit_wo = -amount_wo
                amount_currency_wo = -abs(amount_currency_wo)
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
        invoice.register_payment(counterpart_aml)

        # Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)

        move.post()
        return move

    # Coloca la informacion del metodo onchange que se encuentra como readonly
    @api.constrains('journal_id')
    def Validar_Forma_Pago(self):

        if self.timbrar_pago == False:
            return;

        # Valida que haya elegido una forma de pago
        if self.payment_type == "inbound":
            if self.ref != False:
                if self.formadepagop_id.id != False:
                    # Valida el ingreso de datos Bancarios
                    if self.formadepagop_id.descripcion != "Efectivo":
                        if self.journal_id.type == "bank":
                            if self.formadepagop_id.rfc_emisor_cta_benef != "No":
                                self.cta_beneficiario = self.journal_id.bank_acc_number
                                """Esta linea de codigo fue comentada ya que apartir de ahora de utilizara un catalago de bancos precargado.
                                Anteriormente utilizaba del banco del diario para realizar este paso de informacion, pero con la nueva forma
                                a quedado obsoleto por lo que ha sido comentado en caso de que sea requerido para instalaciones anteriores"""
                                # self.nom_banco_ord_ext_id = self.journal_id.bank_id.name
                                # self.rfc_emisor_cta_ben = self.journal_id.rfc_institucion_bancaria
                                # self.tipocambiop = self.currency_id.inverse_rate
                            if self.formadepagop_id.rfc_emisor_cta_benef != "No":
                                # Valida el patron de la cuenta Beneficiara
                                patron_cta_benef = self.formadepagop_id.patron_cta_benef
                            # Valida que la Cuenta Beneficiaria no este vacia
                            if self.cta_beneficiario != False:
                                if patron_cta_benef != "No":
                                    rule_patron_cta_benef = re.compile(patron_cta_benef)
                                    if not rule_patron_cta_benef.search(self.cta_beneficiario):
                                        msg = "Formato de Cuenta Beneficiaria Incorrecto para la forma de pago: " + str(
                                            self.formadepagop_id.descripcion)
                                        raise ValidationError(msg)
                            # Valida el patron de la cuenta ordenante
                            patron_cta_ordenante = self.formadepagop_id.patron_cta_ordenante
                            if self.cta_ordenante != False:
                                if patron_cta_ordenante != "No":
                                    rule_patron_cta_ordenante = re.compile(patron_cta_ordenante)
                                    if not rule_patron_cta_ordenante.search(self.cta_ordenante):
                                        msg = "Formato de Cuenta Ordenante Incorrecto para la forma de pago: " + str(
                                            self.formadepagop_id.descripcion)
                                        raise ValidationError(msg)
                else:
                    if self.es_proveedor == False:
                        raise ValidationError("No ha ingresado la forma de pago")

    @api.multi
    def Validar_y_Timbrar_Pago(self):
        for record in self:
            if record.payment_type == "inbound":
                if record.state != "posted":
                    # record.GuardaGeneralesPago(record);
                    record.post()
                record.generar_timbre();

    def Validar_Pago(self):
        if self.payment_type == "inbound":
            self.GuardaGeneralesPago(self);
            self.post();

        if self.payment_type == "outbound":
            self.post()

    def _validacionTimbre(self):
        if self.sustituye_pago == True and (self.pago_sustituye.id == False or self.pago_sustituye.id == None):
            raise ValidationError("No se ha seleccionado el pago a sustituir")

        # Valida que las facturas asignadas tengan uuid para timbrar
        for documento in self.documentos_relacionados:
            if documento.uuid_documento == None or documento.uuid_documento == False:
                print(documento.invoice_id)
                raise ValidationError(
                    "No se puede timbrar una pago con facturas no timbradas (%s)" % (documento.invoice_id.number))

    def GuardaGeneralesPago(self, record):
        if record.payment_type == "inbound":
            # Incremento el numero de parcilidad
            par = str(int(record.invoice_ids.no_parcialidad) + 1)
            # self.invoice_ids.no_parcialidad = par
            record.no_parcialidad = par
            residual_antes_de_pago = record.invoice_ids.residual
            # record.imp_saldo_ant = residual_antes_de_pago;

            if record.journal_id.type == "bank":
                record.cta_beneficiario = record.journal_id.bank_acc_number
                record.rfc_emisor_cta_ben = record.journal_id.rfc_institucion_bancaria
                # self.tipocambiop = self.currency_id.inverse_rate

                # record.imp_saldo_ant = record.invoice_ids.residual;
                if record.currency_id == record.invoice_ids.currency_id and record.currency_id.name == 'USD':
                    record.imp_pagado = record.amount;
                else:
                    if Decimal(record.tipocambio_oper) == 1.0:
                        record.imp_pagado = record.amount;
                    else:
                        valor_antes = (Decimal(record.amount)) * (Decimal(record.tipocambio_oper));
                        record.imp_pagado = (math.floor(valor_antes * 100) / 100.0) if round else valor_antes
                        # record.imp_pagado = (Decimal(record.amount))* (Decimal(record.tipocambio_oper));

                        # print(math.floor(record.imp_pagado))
                        # record.imp_pagado = record.currency_id.round(record.imp_pagado) if round else record.imp_pagado
                        # record.imp_pagado = (math.floor(record.imp_pagado*100)/100) if round else record.imp_pagado

                # record.imp_saldo_insoluto = (Decimal(record.imp_saldo_ant))-(Decimal(record.imp_pagado))

            # record.write({'imp_saldo_insoluto':record.imp_saldo_insoluto})

        # self.moneda_p = self.currency_id.id;

    @api.multi
    def descargar_factura_pdf(self):

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])
        url_descarga_pdf = url_parte.url + self.pdf + self.fac_id
        return {
            'type': 'ir.actions.act_url',
            'url': url_descarga_pdf,
            'target': 'new',
        }

    @api.multi
    def obtiene_forma_pago(self, access_uid=None):
        """ Update form view id of action to open the invoice """
        if self.payment_type in ('inbound', 'in_refund'):
            # return self.env.ref('sft-facturacion.account_payment_sft_pago_view').id
            return self.env.ref('sft-facturacion.account_payment_sft_pago_view').id
        else:
            return self.env.ref('account.view_account_payment_form').id

    @api.multi
    def descargar_factura_xml(self):

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])
        url_descarga_xml = url_parte.url + self.xml + self.fac_id
        return {
            'type': 'ir.actions.act_url',
            'url': url_descarga_xml,
            'target': 'new',
        }

    def generar_timbre(self):
        self._validacionTimbre();

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])
        url = str(url_parte.url) + "webresources/FacturacionWS/Facturar"

        factura = self.env['account.invoice'].search([('number', '=', self.ref)])

        # impuesto_iva = ""
        # lineas = []
        # for lineas_de_factura in factura.invoice_line_ids:
        #     for taxs in lineas_de_factura.invoice_line_tax_ids:
        #         if taxs.tipo_impuesto_id.descripcion == "IVA":
        #             impuesto_iva = taxs.tasa_o_cuota_id.valor_maximo

        # Datos del Usuario de Conectividad
        usuario = url_parte.usuario
        #encrypted = url_parte.encriptada;

        contrasena=url_parte.contrasena
        string=str(contrasena)
        #crea el algoritmo para encriptar la informacion
        algorithim=hashlib.md5()
        #encripta la informacion
        algorithim.update(string.encode('utf-8'))
        #La decodifica en formato hexadecimal
        encrypted=algorithim.hexdigest()


        
        ts = time.time()
        tz = pytz.timezone('America/Monterrey')
        ct = datetime.datetime.now(tz=tz).strftime('%H:%M:%S')
        tiempo = time.strftime("%H:%M:%S")
        timestamp = time.strftime('%Y/%m/%d %H:%M:%S')
        # fecha_pago = factura.date_invoice+"T"+str(ct)
        fecha_pago = self.payment_date + "T" + str(ct)

        if self.nom_banco_ord_ext_id == False:
            self.nom_banco_ord_ext_id = ""

        if self.cta_ordenante == False:
            self.cta_ordenante = ""

        if self.rfc_emisor_cta_ben == False:
            self.rfc_emisor_cta_ben = ""

        if self.cta_beneficiario == False:
            self.cta_beneficiario = ""

        if self.rfc_emisor_cta_ben == False:
            self.rfc_emisor_cta_ben = ""

        num_operacion = "";
        if self.no_operacion != False:
            num_operacion = self.no_operacion;

        documentos = [];

        for documento in self.documentos_relacionados:
            json_documento = {};
            json_documento["id_documento"] = documento.uuid_documento;
            json_documento["serie"] = documento.invoice_id.fac_serie;
            json_documento["folio"] = documento.invoice_id.fac_folio;
            json_documento["moneda_dr"] = documento.moneda_dr;
            json_documento["tipo_cambio_dr"] = documento.tipocambio_dr;
            json_documento["metodo_de_pago_dr"] = documento.invoice_id.metodo_pago_id.c_metodo_pago;
            json_documento["num_parcialidad"] = "1";
            json_documento["imp_pagado"] = str(documento.importe_pagado);
            json_documento["imp_saldo_ant"] = str(documento.imp_saldo_ant);
            json_documento["imp_saldo_insoluto"] = str(documento.imp_saldo_insoluto);
            documentos.append(json_documento);

        # Estructura Json
        data = {
            "factura": {
                "fecha_facturacion": timestamp,
                "odoo_contrasena": encrypted,
                "fac_tipo_cambio": 1,
                "fac_moneda": "XXX",
                "fac_tipo_comprobante": "P",
                "fac_importe": 0,
                "receptor_uso_cfdi": self.uso_cfdi_id.c_uso_cfdi,
                "user_odoo": url_parte.usuario,
                "receptor": {
                    "receptor_id": self.partner_id.vat,
                    "NIF": str(self.partner_id.nif),
                    "correo": self.partner_id.email,

                },
                "fac_lugar_expedicion": self.env.user.company_id.zip,
                # "fac_porcentaje_iva": impuesto_iva,
                "conceptos": [{
                    "con_subtotal": "0.0",
                    "con_valor_unitario": "0.0",
                    "con_importe": "0.0",
                    "con_cantidad": "1",
                    "con_unidad_clave": "ACT",
                    "con_clave_prod_serv": "84111506",
                    "con_descripcion": "Pago",
                    "con_total": "0.0"
                }],
                "emisor_id": str(self.env.user.company_id.company_registry),
                "fac_no_orden": self.name,
                "fac_emisor_regimen_fiscal_descripcion": self.env.user.company_id.property_account_position_id.name,
                "fac_emisor_regimen_fiscal_key": self.env.user.company_id.property_account_position_id.c_regimenfiscal,
                "pago": {
                    "fecha_pago": fecha_pago,
                    "forma_de_pago": str(self.formadepagop_id.c_forma_pago),
                    "moneda": str(self.currency_id.name),
                    "tipo_cambio": str(self.tipocambiop),
                    # "monto": str(self.imp_pagado),
                    "monto": str(self.amount),
                    "num_operacion": num_operacion,
                    # "rfc_emisor_cta_ord": str(factura.partner_id.nif),
                    "rfc_emisor_cta_ord": str(self.rfc_emisor_cta_ord),
                    "nom_banco_ord_ext_id": str(self.nom_banco_ord_ext_id.c_nombre),
                    "cta_ordenante": str(self.cta_ordenante),
                    "rfc_emisor_cta_ben": str(self.rfc_emisor_cta_ben),
                    "cta_beneficiario": str(self.cta_beneficiario),
                    "documentos": documentos
                }
            }
        }

        # "documentos": [
        #                 {
        #                     "id_documento": str(factura.uuid),
        #                     "serie": factura.fac_serie,
        #                     "folio": factura.fac_folio,
        #                     "moneda_dr": str(factura.currency_id.name),
        #                     "tipo_cambio_dr": str(self.tipocambio_oper),
        #                     "metodo_de_pago_dr": 'PPD',
        #                     "num_parcialidad": str(self.no_parcialidad),
        #                     "imp_pagado": str(self.imp_pagado),
        #                     "imp_saldo_ant": str(self.imp_saldo_ant),
        #                     "imp_saldo_insoluto": str(self.imp_saldo_insoluto)
        #                 }
        #             ]

        # Coloca datos de Receptor (no obligatorios)
        if self.partner_id.state_id.name != None and self.partner_id.state_id.name != False:
            data["factura"]["receptor"]["estado"] = self.partner_id.state_id.name;

        if self.partner_id.name != None and self.partner_id.name != False:
            data["factura"]["receptor"]["compania"] = self.partner_id.name;

        if self.partner_id.city != None and self.partner_id.city != False:
            data["factura"]["receptor"]["ciudad"] = self.partner_id.city;

        if self.partner_id.street != None and self.partner_id.street != False:
            data["factura"]["receptor"]["calle"] = self.partner_id.street;

        if self.partner_id.zip != None and self.partner_id.zip != False:
            data["factura"]["receptor"]["codigopostal"] = self.partner_id.zip;

        if self.partner_id.colonia != None and self.partner_id.colonia != False:
            data["factura"]["receptor"]["colonia"] = self.partner_id.colonia;

        if self.partner_id.numero_ext != None and self.partner_id.numero_ext != False:
            data["factura"]["receptor"]["numero_ext"] = self.partner_id.numero_ext;

        # CFDIRelacionados (Para reemplazo de pagos)
        if self.sustituye_pago == True:
            cfdi_relacionados = []
            cfdi_relacionado = {
                "uuid": self.pago_sustituye.uuid
            }
            cfdi_relacionados.append(cfdi_relacionado)
            data["factura"]["cfdi_relacionados"] = cfdi_relacionados;
            data["factura"]["fac_tipo_relacion"] = "04";

            # Actualiza el otro a Reemplazado
            self.pago_sustituye.write({"state": "replaced"});

        headers = {
            'content-type': "application/json", 'Authorization': "Basic YWRtaW46YWRtaW4="
        }
        self._logger.info(data)

        json_data = json.dumps(data);
        response = requests.request("POST", url, data=json_data, headers=headers)
        json_data = json.loads(response.text)
        if json_data['result']['success'] == 'true':
            self.timbrada = 'Timbrada'
            # En caso de recibir una respuesta positiva anexa el uuid al formulario de la factura timbrada
            self.uuid = json_data['result']['uuid']
            self.fac_id = json_data['result']['fac_id']
        else:
            raise ValidationError(json_data['result']['message'])

    @api.multi
    def cancelar(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                move.button_cancel()
                move.unlink()
            rec.state = 'cancelled'

    @api.multi
    def cancelar_pagos_timbrada(self):

        self.cancelar();

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])
        url = str(url_parte.url)+"webresources/FacturacionWS/Cancelar"
        # print "1"
        data = {
            "uuid": self.uuid
        }

        headers = {
            'content-type': "application/json", 'Authorization': "Basic YWRtaW46YWRtaW4="
        }

        self._logger.info(json.dumps(data));
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text);
        json_data = json.loads(response.text)
        if json_data['result']['success'] == 'true' or json_data['result']['success'] == True:
            self.timbrada = 'Pago Cancelado'
            self.state = "cancelled";

        else:
            raise ValidationError(json_data['result']['message'])


class AccountPaymentDocto(models.Model):
    _name = 'account.payment.docto'

    _logger = logging.getLogger(__name__)

    @api.model
    @api.one
    def getDomain(self):
        if self:
            if self.payment_id and self.payment_id != False and self.payment_id.partner_id and self.payment_id.partner_id != None:
                self.id_cliente = self.payment_id.partner_id.id;
                facturas = self.env['account.invoice'] \
                    .search([('partner_id', '=', self.payment_id.partner_id.id),
                             ('residual', '>', 0.0),
                             ('state', 'in', ['timbrada', 'open']),
                             ('fac_timbrada', '=', 'Timbrada')
                             ]);
                self.domain_facturas = facturas
                # return facturas;
                # return [('id', 'in', facturas.mapped("id"))]
                return [('id', 'in', facturas.mapped("id"))];
        return [];

    @api.depends('id_cliente', 'domain_facturas')
    @api.one
    def domain_invoice(self):
        if self:
            if self.payment_id and self.payment_id != False and self.payment_id.partner_id and self.payment_id.partner_id != None:
                facturas = self.env['account.invoice'] \
                    .search([('partner_id', '=', self.payment_id.partner_id.id),
                             ('residual', '>', 0.0),
                             ('state', 'in', ['timbrada', 'open']),
                             ('fac_timbrada', '=', 'Timbrada')
                             ]);
                # return facturas;
                return [('id', 'in', facturas.mapped("id"))]

                # return facturas.mapped("id");
        return [];

    domain_facturas = fields.One2many('account.invoice', string='filtro', store=False, default=getDomain,
                                      compute=getDomain)
    # invoice_id = fields.Many2one('account.invoice', string="Factura")

    # invoice_id = fields.Many2one('account.invoice', string="Factura", domain=getDomain )
    # domain=lambda self:[('partner_id','=',self.payment_id.partner_id.id),
    #                          ('residual','>',0.0 ),
    #                          ('state','in',['timbrada','open']),
    #                          ('fac_timbrada','=','Timbrada')
    #                          ]
    # invoice_id = fields.Many2one('account.invoice', string="Factura", domain= lambda self: self.getDomain() )
    # invoice_id = fields.Many2one('account.invoice', string="Factura", domain= getDomain )
    invoice_id = fields.Many2one('account.invoice', string="Factura")
    # invoice_id = fields.Many2one('account.invoice', string="Factura" )
    #
    payment_id = fields.Many2one('account.payment', string="Pago")
    importe_pagado = fields.Float("Importe pagado", store=True, compute="_computeDocumento", help="Importe pagado a la facutura, se calcula en base al tipo de cambio y el Importe pagado pago")
    importe_pagado_moneda = fields.Float("Importe moneda pago", store=True, help="Importe a capturar conforme a la moneda del pago")  # compute="_calculaImporteTC"
    #tipocambio_dr = fields.Float('TC Factura', store=True, compute="_computeDocumento")  # compute="_calculaImporteTC"
    tipocambio_dr = fields.Float('TC Factura', store=False, compute="_computeDocumento")  # compute="_calculaImporteTC"
    moneda_dr = fields.Char("Moneda", compute="_computeDocumento", store=True)
    uuid_documento = fields.Char("UUID", compute="_computeDocumento")
    serie = fields.Char("Serie", compute="_computeDocumento")
    folio = fields.Char("Folio", compute="_computeDocumento")
    imp_saldo_ant = fields.Float('Saldo Anterior', store=True)
    # compute="_computeDocumento",
    imp_saldo_insoluto = fields.Float('Importe Saldo Insoluto', compute="_computeDocumento", store=True)

    @api.multi
    def write(self, vals):
        return super(AccountPaymentDocto, self).write(vals)

    @api.multi
    def create(self, vals):
        invoice = self.env['account.invoice'].browse(vals["invoice_id"]);
        vals["uuid_documento"] = invoice.uuid;
        vals["moneda_dr"] = invoice.currency_id.name;
        vals["imp_saldo_ant"] = invoice.residual;
        return super(AccountPaymentDocto, self).create(vals)

    id_cliente = fields.Integer()

    @api.model
    @api.depends('invoice_id', 'importe_pagado_moneda')
    @api.one
    def _computeDocumento(self):
        # print("_computeDocumento")
        total = 0;
        model_currency = self.env['res.currency'];
        for linea in self:
            for factura in linea.invoice_id:
                linea.uuid_documento = factura.uuid;
                linea.moneda_dr = factura.currency_id.name;
                linea.serie = factura.fac_serie;
                linea.folio = factura.fac_folio;
                #linea.imp_saldo_insoluto = (Decimal(linea.imp_saldo_ant)) - (Decimal(linea.importe_pagado))

                # linea.tipocambio_dr = linea.payment_id.currency_id.round(model_currency.with_context(date=linea.payment_id.payment_date)._get_conversion_rate(linea.payment_id.currency_id, linea.invoice_id.currency_id))
                tc = model_currency.with_context(date=linea.payment_id.payment_date)._get_conversion_rate(
                    linea.payment_id.currency_id, linea.invoice_id.currency_id);
                # tc = 1.0/tc;
                linea.tipocambio_dr = linea.payment_id.currency_id.round(tc)

                if float(linea.tipocambio_dr) > 0:
                    linea.importe_pagado = linea.importe_pagado_moneda * float(linea.tipocambio_dr);
                    # linea.importe_pagado_moneda = linea.importe_pagado / float(linea.tipocambio_dr) ;

                else:
                    linea.importe_pagado = 0;
                    # linea.importe_pagado_moneda = 0 ;

                linea.imp_saldo_insoluto = (Decimal(linea.imp_saldo_ant)) - (Decimal(linea.importe_pagado))

            # linea.payment_id.amount =linea.payment_id.amount +linea.importe_pagado_moneda;
            # linea.payment_id.amount = linea.payment_id.amount + linea.importe_pagado_moneda;

    @api.model
    @api.onchange('invoice_id')
    @api.multi
    def _changeInvoice(self):
        model_currency = self.env['res.currency'];
        for linea in self:
            for factura in linea.invoice_id:
                linea.uuid_documento = factura.uuid;
                linea.moneda_dr = factura.currency_id.name;
                linea.imp_saldo_ant = factura.residual;
                linea.serie = factura.fac_serie;
                linea.folio = factura.fac_folio;
                linea.imp_saldo_insoluto = (Decimal(linea.imp_saldo_ant)) - (Decimal(linea.importe_pagado))

                tc = model_currency.with_context(date=linea.payment_id.payment_date)._get_conversion_rate(
                    linea.payment_id.currency_id, linea.invoice_id.currency_id);
                tc = 1.0 / tc;
                linea.tipocambio_dr = linea.payment_id.currency_id.round(tc)

    # @api.model
    # @api.depends('importe_pagado')
    # @api.one
    # def _calculaImporteTC(self):
    #     for pago in self:
    #         if pago.importe_pagado != None and pago.invoice_id != None and pago.invoice_id != False and len(pago.invoice_id) > 0:
    #             pago.imp_saldo_insoluto =  pago.imp_saldo_ant - pago.importe_pagado;
    #             #print(pago.payment_id.currency_id)
    #             #print( pago.invoice_id.currency_id )
    #             if pago.payment_id != None and pago.payment_id != False:
    #                 print(pago.payment_id.payment_date)
    #                 model_currency = self.env['res.currency'];
    #                 #pago.tipocambio_oper = pago.payment_id.currency_id.round(model_currency.with_context(date=pago.payment_id.payment_date)._get_conversion_rate(pago.payment_id.currency_id, pago.invoice_id.currency_id))
    #                 #pago.tipocambio_dr = pago.payment_id.currency_id.round(model_currency.with_context(date=pago.payment_id.payment_date)._get_conversion_rate(pago.payment_id.currency_id, pago.invoice_id.currency_id))
    #                 #pago.tipocambio_dr = pago.payment_id.currency_id.round(model_currency.with_context(date=pago.payment_id.payment_date)._get_conversion_inverse_rate(pago.payment_id.currency_id, pago.invoice_id.currency_id))
    #
    #                 currency_pesos = model_currency.search([('name', '=', 'MXN')])
    #                 if currency_pesos == None or len(currency_pesos)==0:
    #                     pago.tipocambio_dr = 1;
    #                 else:
    #                     tc = model_currency.with_context(date=pago.payment_id.payment_date)._get_conversion_rate(currency_pesos[0],pago.invoice_id.currency_id);
    #                     print(str(tc))
    #                     pago.tipocambio_dr =  currency_pesos[0].round(1/tc)
    #
    #
    #         else:
    #             pago.tipocambio_dr = None;
    #             pago.importe_pagado_moneda = None;

    @api.model
    @api.onchange("invoice_id")
    def _get_change_documento(self):
        self._computeDocumento();

    # @api.onchange('importe_pagado_moneda')
    # @api.constrains('importe_pagado_moneda')
    # def _cng_importe_pagado_moneda(self):
    #     for pago in self:
    #         if pago.invoice_id:
    #             # if pago.imp_saldo_ant <= 0.0:
    #             #     raise ValidationError("El saldo a pagar debe ser mayor a 0.0 : %s" % pago.imp_saldo_ant)
    #             #
    #             # if pago.importe_pagado <= 0.0:
    #             #     raise ValidationError("El importe a pagar debe ser mayor a 0.0 : %s" % pago.importe_pagado)
    #             print("Constraint")
    #             print(str(pago.importe_pagado))
    #             print(str(pago.imp_saldo_ant))
    #             # if pago.importe_pagado > pago.imp_saldo_ant:
    #             #     raise ValidationError("El importe a pagar (%s) debe ser menor o igual al saldo anterior (%s)"%(pago.importe_pagado, pago.imp_saldo_ant) )

    # @api.constrains('importe_pagado')
    # def _check_importe_pagado(self):
    #     for pago in self:
    #         if pago.imp_saldo_ant <= 0.0:
    #             raise ValidationError("El saldo a pagar debe ser mayor a 0.0 : %s" % pago.imp_saldo_ant)
    #
    #         if pago.importe_pagado <= 0.0:
    #             raise ValidationError("El importe a pagar debe ser mayor a 0.0 : %s" % pago.importe_pagado)
    #
    #         if pago.importe_pagado <= pago.imp_saldo_ant:
    #             raise ValidationError("El importe a pagar debe ser menor o igual al saldo anterior " )

    # @api.model
    # @api.onchange("importe_pagado")
    # def _get_change_importe(self):
    #     print("_get_change_importe")
    #
    #     for pago in self:
    #         if pago.importe_pagado != None:
    #             pago.imp_saldo_insoluto =  pago.imp_saldo_ant - pago.importe_pagado;
    #             print(pago.payment_id.currency_id)
    #             print( pago.invoice_id.currency_id )
    #             if pago.payment_id != None and pago.payment_id != False:
    #                 print(pago.payment_id.payment_date)
    #                 model_currency = self.env['res.currency'];
    #                 pago.tipocambio_oper = pago.payment_id.currency_id.round(model_currency.with_context(date=pago.payment_id.payment_date)._get_conversion_rate(pago.payment_id.currency_id, pago.invoice_id.currency_id))
    #                 print(pago.tipocambio_oper)
    #                 if float(pago.tipocambio_oper) >0:
    #                     pago.importe_pagado_moneda = pago.importe_pagado / float(pago.tipocambio_oper) ;
    #                 else:
    #                     pago.importe_pagado_moneda = 0 ;
    #         else:
    #             pago.tipocambio_oper = None;
    #             pago.importe_pagado_moneda = None;


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = 'account.journal'

    # todo add omar
    @api.onchange('bank_id')
    def actualizar_rfc(self):
        self.rfc_institucion_bancaria = self.bank_id.banco_sft.rfc_banco

    rfc_institucion_bancaria = fields.Char('RFC Institucion Bancaria', size=12)


    @api.constrains('rfc_institucion_bancaria')
    def ValidarRFCInstitucionBancaria(self):
        if self.rfc_institucion_bancaria != False:
            if len(self.rfc_institucion_bancaria) != 12:
                raise ValidationError(
                    "El RFC %s no tiene la logitud de 12 caracteres para personas Morales que establece el sat" % (
                    self.rfc_institucion_bancaria))
            else:
                patron_rfc = re.compile(r'^([A-ZÑ\x26]{3}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                if not patron_rfc.search(self.rfc_institucion_bancaria):
                    msg = "Formato RFC de Persona Moral Incorrecto"
                    raise ValidationError(msg)

    @api.constrains('bank_acc_number')
    def ValidarNoCuentaBancaria(self):
        if self.bank_acc_number != False:
            patron_rfc = re.compile(r'[0-9]{10,11}|[0-9]{15,16}|[0-9]{18}|[A-Z0-9_]{10,50}')
            if not patron_rfc.search(self.bank_acc_number):
                msg = "Formato Incorrecto del No. Cuenta"
                raise ValidationError(msg)


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    _logger = logging.getLogger(__name__)
    metodo_pago_id = fields.Many2one('cfdi.metodo_pago',string='Metodo de pago')



#TODO ADD OMAR eliminar eliminar eliminar eliminar
class CfdiBankPartner(models.Model):
    _name = 'cfdi.bank.partner'

    banco = fields.Many2one('cfdi.bancos')
    cuenta = fields.Char()
    partner_id = fields.Many2one('res.partner')


# usado para gestionar gestionar cuentas bancarias de clientes
#TODO ADD OMAR
class CfdiBankPartner(models.Model):
    _name = 'cuenta.bancaria.sft'

    @api.onchange('partner_id')
    def onchangePartner(self):
        self.titular = self.partner_id.name

    name = fields.Char(string='Numero de cuenta') #cuenta
    banco = fields.Many2one('cfdi.bancos', string='Banco')
    titular = fields.Char(string='Nombre del Titular de la cuenta')
    partner_id = fields.Many2one('res.partner')


# creo relacion entre banco de odoo y banco sft y establece el nombre de este en el de banco de odoo
# todo add omar
class ResBank(models.Model):
    _inherit = 'res.bank'

    @api.onchange('banco_sft')
    def onChangeBancoSFT(self):
        self.name = self.banco_sft.c_nombre



    banco_sft = fields.Many2one('cfdi.bancos', string='Banco SFT') #podria ser 'required', y podria ponerse 'name' (modelo actual) como readonly para forzar la union entre banco sft y banco de odoo

