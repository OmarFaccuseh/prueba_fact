# -*- coding: utf-8 -*-

import webbrowser
import hashlib
import json
import ctypes
import os
import base64
import requests
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging
from pytz import timezone
import time, pytz

# Comentario agregado
# segundo comentario
# Agrega al formulario los capos requeridos por el Sat
BASE_ = base64

class localizacion_mexicana(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice']

    _logger = logging.getLogger(__name__)

    uuid = fields.Char(string="UUID")
    cfdi_relacionados = fields.Char(string='CFDI Relacionados')
    invoice_relacionados = fields.Many2many('account.invoice', 'cfdisrelacionados', 'field_1', 'field_2', string='Documentos relacionados')  # fields.One2many('account.invoice.docto', 'invoice_id', string='Documentos relacionados')

    @api.depends('partner_id')
    def compute_id_partner(self):
        if self.partner_id:
            self.id_partner = self.env['res.partner'].search([('id', '=', self.partner_id.id)]).id
        else:
            self.id_partner = 0

    id_partner = fields.Integer( compute='compute_id_partner' )


    #Variables del receptor

    def default_cliente_rfc(self):
        if self.partner_id.vat == False:
            if self.partner_id.nif != False:
                self.rfc_cliente_factura = self.partner_id.nif
        else:
            self.rfc_cliente_factura = self.partner_id.vat

    rfc_cliente_factura = fields.Char(string='RFC Receptor')

    def default_company_rfc(self):
        return self.env.user.company_id.company_registry

    def default_company_calle(self):
        return self.env.user.company_id.street

    def default_company_ciudad(self):
        return self.env.user.company_id.city

    def default_company_pais(self):
        return self.env.user.company_id.country_id.name


    def default_company_estado(self):
        return self.env.user.company_id.state_id.name

    @api.one
    def puede_empezar_pagar(self):
        None;
        if self.type not in "out_invoice":
            self.puede_pagar = False;
            return False;
        if (self.state == 'timbrada' or self.state == 'validate'):
            self.puede_pagar = False;

            return False;

        self.puede_pagar = True;
        return True;

    # Variables de la compañia
    compania_calle = fields.Char(string='Calle', readonly=True, default=default_company_calle)
    compania_ciudad = fields.Char(string='Ciudad', readonly=True, default=default_company_ciudad)
    compania_estado = fields.Char(string='Estado', readonly=True, default=default_company_estado)
    compania_pais = fields.Char(string='Pais', readonly=True, default=default_company_pais)
    no_parcialidad = fields.Char(string="Pagos Realizados", default="0")
    rfc_emisor = fields.Char(string='RFC Emisor', default=default_company_rfc)
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('timbrada', 'CFDI'),
            ('timbrado cancelado', 'CFDI Cancelado'),
            ('open', 'Open'),
            ('validate', 'Validada'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.", color="green")


    forma_pago_id = fields.Many2one('cfdi.forma_pago',string='Forma Pago')  #todo add omar defaul=default_forma_pago
    metodo_pago_id = fields.Many2one('cfdi.metodo_pago',string='Metodo de pago')
    #codigo_postal_id = fields.Many2one('cfdi.codigo_postal',string='Lugar de Expedicion',default=default_lugar_de_expedicion)
    uso_cfdi_id = fields.Many2one('cfdi.uso_cfdi', string='Uso CFDI')
    fac_id = fields.Char()
    observaciones = fields.Text(string='Observaciones')
    tipo_de_relacion_id = fields.Many2one('cfdi.tipo_relacion',string='Tipo de Relacion')
    pdf = "Factura?Accion=descargaPDF&factura=";
    xml = "Factura?Accion=ObtenerXML&factura=";
    fac_timbrada = fields.Char('CFDI', default="Sin Timbrar",readonly=True, copy=False)
    fac_folio = fields.Char('Folio CFDI', readonly=True, copy=False)
    fac_serie = fields.Char('Serie CFDI', readonly=True, copy=False)
    fac_estatus_cancelacion = fields.Char("Estatus Cancelación", default="", copy=False)
    tipo_cambio = fields.Float('Tipo de cambio')

    puede_pagar = fields.Boolean("Puede pagar", store=False, compute=puede_empezar_pagar);



    #Carga El RFC del Cliente Seleccionado
    @api.onchange('partner_id')
    def _onchange_rfc_emisor(self):
        if self.partner_id.vat == False:
            if self.partner_id.nif != False:
                self.rfc_cliente_factura = self.partner_id.nif
        else:
            self.rfc_cliente_factura = self.partner_id.vat
            if self.partner_id.metodo_pago_id.c_metodo_pago!= False:
                self.metodo_pago_id = self.partner_id.metodo_pago_id.id
            if self.partner_id.uso_cfdi_id.c_uso_cfdi!=False:
                self.uso_cfdi_id = self.partner_id.uso_cfdi_id.id

    @api.onchange('currency_id','date_invoice')
    def _onchange_currency_id(self):
        print("_onchange_currency_id")
        if self.currency_id == self.env.user.company_id.currency_id:
            self.tipo_cambio = 1;
            return;


        if self.date_invoice == None or self.date_invoice == False:
            return;

        currency = self.currency_id
        tipo_cambio  = currency.with_context(dict(self._context or {}, date=self.date_invoice))
        print(tipo_cambio)
        if tipo_cambio != None:
            print(tipo_cambio.inverse_rate)
            self.tipo_cambio = tipo_cambio.inverse_rate;

        return;

    @api.onchange('payment_term_id')
    def _onchange_payment_term(self):
        for factura in self:
            if factura.payment_term_id and factura.payment_term_id.metodo_pago_id:
                factura.metodo_pago_id = factura.payment_term_id.metodo_pago_id;

    def convert_TZ_UTC(self, TZ_datetime):
        os.environ['TZ'] = 'America/Mexico_City'
        #time.tzset()
        pytz.timezone("America/Mexico_City")

        # tz_orig = os.environ['TZ']
        # tz=tz_orig
        # try:
        #     if (tz != tz_orig):
        #         os.environ['TZ'] = tz
        #         time.tzset()
        #
        #     dt = datetime.datetime.fromtimestamp(utc)
        #     return (dt.strftime("%Y%m%d"), dt.strftime("%H%M%S"))
        #
        # finally:
        #
        #     if (os.environ['TZ'] != tz_orig):
        #         os.environ['TZ'] = tz_orig
        #         time.tzset()


        fmt = "%Y-%m-%d %H:%M:%S"
        # Current time in UTC
        now_utc = datetime.now(timezone('UTC'))
        #print("default_tmz")
        #print(now_utc)
        # Convert to current user time zone
        now_timezone = now_utc.astimezone(timezone(self.env.user.tz))
        UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(now_timezone.strftime(fmt), fmt)
        local_datetime = datetime.strptime(TZ_datetime, fmt)
        result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
        return result_utc_datetime.strftime(fmt)

    # @api.onchange('product_id')
    # def _onchange_product_id_sft(self):
    #     domain = {}
    #     if not self.invoice_id:
    #         return
    #
    #     part = self.invoice_id.partner_id
    #     fpos = self.invoice_id.fiscal_position_id
    #     company = self.invoice_id.company_id
    #     currency = self.invoice_id.currency_id
    #     type = self.invoice_id.type
    #
    #     if not part:
    #         warning = {
    #                 'title': _('Warning!'),
    #                 'message': _('You must first select a partner!'),
    #             }
    #         return {'warning': warning}
    #
    #     if not self.product_id:
    #         if type not in ('in_invoice', 'in_refund'):
    #             self.price_unit = 0.0
    #         domain['uom_id'] = []
    #     else:
    #         if part.lang:
    #             product = self.product_id.with_context(lang=part.lang)
    #         else:
    #             product = self.product_id
    #
    #         self.name = product.partner_ref
    #         account = self.get_invoice_line_account(type, product, fpos, company)
    #         if account:
    #             self.account_id = account.id
    #         self._set_taxes()
    #
    #         if type in ('in_invoice', 'in_refund'):
    #             if product.description_purchase:
    #                 self.name += '\n' + product.description_purchase
    #         else:
    #             if product.description_sale:
    #                 self.name += '\n' + product.description_sale
    #
    #         if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
    #             self.uom_id = product.uom_id.id
    #         domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]
    #
    #         if company and currency:
    #             if company.currency_id != currency:
    #                 print("Antes")
    #                 print(self.invoice_id.date_invoice)
    #                 print("Despues")
    #                 print(self.convert_TZ_UTC(self.invoice_id.date_invoice))
    #                 self.price_unit = self.price_unit * currency.with_context(dict(self._context or {}, date=self.convert_TZ_UTC(self.invoice_id.date_invoice))).rate
    #
    #             if self.uom_id and self.uom_id.id != product.uom_id.id:
    #                 self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
    #     return {'domain': domain}



    @api.constrains('state')
    def limpiar_uuid_al_duplicar_factura(self):
        if self.state == 'draft':
            self.uuid = False
            self.fac_timbrada = 'Sin Timbrar';

    @api.multi
    def timbrar(self):
        print("Timbrar")
        print(self.state)
        print("Simona")
        if self.state not in ['proforma2', 'draft', 'validate']:
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        self.action_date_assign()
        self.action_move_create()
        return self.invoice_validate()


    @api.multi
    def registro_pago(self):
        if self:
            print("Regiostro de pago")

            # todo add omar  agregue el if no el else
            ceuntas_partner = self.partner_id.mis_cuentas.ids  # [0].banco.id  del cliente      ->>>  add bank_ids
            journals = self.env['account.journal'].search([('active', '=', True)])
            cta_ben = False
            rfc_ben = ''
            for journal in journals:
                if journal.bank_acc_number:
                    cta_ben = journal.bank_acc_number
                    rfc_ben = journal.rfc_institucion_bancaria
                    break
            if ceuntas_partner:
                primer_cuenta_partner_id = ceuntas_partner[0]
            else:
                primer_cuenta_partner_id = False


            vals = {
                'default_payment_type':'inbound',
                "default_partner_id" : self.partner_id.id,

                "default_cta_ordenante": primer_cuenta_partner_id,
                "default_cta_beneficiario": cta_ben or False,
                "default_rfc_emisor_cta_ben": str(rfc_ben),

                'default_documentos_relacionados':[(0,0,{
                    'invoice_id': self.id,
                    'imp_saldo_ant':self.residual,
                    'moneda_dr':self.currency_id.id,
                    'id_cliente':self.partner_id.id
                    #'uuid_documento': self.uuid
                })]
            }

            return {
                'name': _('Customer Invoice'),
                'view_mode': 'form',
                'view_id': self.env.ref('account.view_account_payment_form').id,
                'res_model': 'account.payment',
                'context': vals,
                'type': 'ir.actions.act_window',
                #'res_id': self.invoice_id.id,
            }
            # return {
            #     'name': _('Customer Invoice'),
            #     'view_type': 'form',
            #     'view_mode': 'form',
            #     'res_model': 'account.payment',
            #     'type': 'ir.actions.act_window',
            #     'nodestroy': True,
            #     'target': 'current',
            #     'res_id':  False,
            #     'view_id': self.env.ref('account.view_account_payment_form').id
            # }

    @api.multi
    def abre_pago(self):
        print("abre_pago")
        # return {
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'account.payment',
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_id':  50 or False,
        #     'target': 'current',
        # }

        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'nodestroy': False,
            'target': 'current',
            'res_id':  50 or False,
        }


    @api.multi
    def reeenviar_factura(self):
        arr_notifica = [];
        for notifica in self.partner_id.partner_notifica_ids:
            arr_notifica.append(notifica["correo"]);

        if len(arr_notifica) == 0:
            raise UserError(_("No se han configurado destinatarios al cliente"))

        self.url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])

        usuario = self.url_parte.usuario


        string = str(self.url_parte.contrasena)
        # crea el algoritmo para encriptar la informacion
        algorithim = hashlib.md5()
        # encripta la informacion
        algorithim.update(string.encode("utf-8"))
        # La decodifica en formato hexadecimal
        encrypted = algorithim.hexdigest()

        # contrasena=self.url_parte.contrasena
        # string=str(contrasena.encode("utf-8"))
        # algorithim=hashlib.md5()
        # algorithim.update(string)
        # encrypted=algorithim.hexdigest()

        factura = str(self.fac_id);

        algorithim = hashlib.md5()
        # encripta la informacion
        algorithim.update(factura.encode("utf-8"))
        # La decodifica en formato hexadecimal
        factura = algorithim.hexdigest()

        # algorithim=hashlib.md5()
        # algorithim.update( str(factura.encode("utf-8")) )
        # factura = algorithim.hexdigest()


        data = {
            "factura": factura,
            "usuario":usuario,
            "contrasena": encrypted,
            "emisor": str(self.rfc_emisor),
            "destinatarios": arr_notifica

        };
        url = str(self.url_parte.url)+"webresources/FacturacionWS/NotificarFacturacion"
        _logger = logging.getLogger(__name__)
        _logger.info(data)

        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        # if True:
        #     return {
        #         "warning":{
        #             "title": "Key Length",
        #             "message": "The length of key is not match",
        #         },
        #     }

        _logger = logging.getLogger(__name__)
        _logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        _logger.info(response.text)
        json_data = json.loads(response.text)
        #Valida que la factura haya sido timbrada Correctamente
        if json_data['result']['success']== 'true':
            return {
                'warning': {
                'title': 'Warning!',
                'message': 'The warning text'}
            }
        else:
            raise ValidationError(json_data['result']['message'])

    @api.multi
    def timbrar_factura(self):
        precision = self.env['decimal.precision'].search([('name', '=','Product Price')])
        if precision == False or precision == None or precision.digits == None:
            raise UserError(_("No se encontró la precisión del producto"))

        decimales = precision.digits;


        self.url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])
        usuario = self.url_parte.usuario
        contrasena=self.url_parte.contrasena
        string=str(contrasena)
        #crea el algoritmo para encriptar la informacion
        algorithim=hashlib.md5()
        #encripta la informacion
        algorithim.update(string.encode('utf-8'))
        #La decodifica en formato hexadecimal
        encrypted=algorithim.hexdigest()
        conceptos = []
        receptor = {}
        if self.partner_id.nif!= False:
            receptor = {
            "receptor_id": self.partner_id.vat,
            "compania":self.partner_id.name,
            "correo":self.partner_id.email,
            # "calle": self.partner_id.street.encode('utf-8'),
            # "ciudad":self.partner_id.city.encode('utf-8'),
            # "correo":self.partner_id.email.encode('utf-8'),
            # "colonia":self.partner_id.colonia.encode('utf-8'),
            # "codigopostal":self.partner_id.zip,
            # "numero_ext":self.partner_id.numero_ext,
            # "estado":self.partner_id.state_id.name.encode('utf-8'),
            "NIF": self.partner_id.nif
        }
        else:
            receptor = {
            "receptor_id": self.partner_id.vat,
            "compania":self.partner_id.name,
            "correo":self.partner_id.email,
            # "calle": self.partner_id.street.encode('utf-8'),
            # "ciudad":self.partner_id.city.encode('utf-8'),
            # "correo":self.partner_id.email.encode('utf-8'),
            # "colonia":self.partner_id.colonia.encode('utf-8'),
            # "codigopostal":self.partner_id.zip,
            # "numero_ext":self.partner_id.numero_ext,
            # "estado":self.partner_id.state_id.name.encode('utf-8'),
        }
        if self.partner_id.numero_int != None and self.partner_id.numero_int != False:
            receptor["numero_int"] = self.partner_id.numero_int;

        if self.partner_id.street != None and self.partner_id.street != False:
            receptor["calle"] = self.partner_id.street;

        if self.partner_id.city != None and self.partner_id.city != False:
            receptor["ciudad"] = self.partner_id.city;

        if self.partner_id.colonia != None and self.partner_id.colonia != False:
            receptor["colonia"] = self.partner_id.colonia;

        if self.partner_id.numero_ext != None and self.partner_id.numero_ext != False:
            receptor["numero_ext"] = self.partner_id.numero_ext;

        if self.partner_id.state_id.name != None and self.partner_id.state_id.name != False:
            receptor["estado"] = self.partner_id.state_id.name;

        if self.partner_id.zip != None and self.partner_id.zip != False:
            receptor["codigopostal"] = self.partner_id.zip;


        arr_notifica = [];
        for notifica in self.partner_id.partner_notifica_ids:
            arr_notifica.append(notifica["correo"]);

        descuento_acumulado = 0.0
        total_acumulado = 0.0
        importe_acumulado = 0.0
        impuesto_acumulado = 0.0


        mpuesto_retenido = 0.0

        for conceptos_record in self.invoice_line_ids:

            importe = conceptos_record.price_subtotal
            importe_acumulado = importe_acumulado+importe
            impuestos = []
            descuento = importe*((conceptos_record.discount)/100)
            descuento_acumulado = descuento_acumulado+descuento
            subtotal = importe

            for impuestos_record in conceptos_record.invoice_line_tax_ids:
                if impuestos_record.traslado_retenido == None or impuestos_record.traslado_retenido ==  False:
                    raise ValidationError("FACT00001: El impuesto %s no  tiene asignado si es Traslado o Retencion" % (impuestos_record.name))

                #Modificación, la base se genera el importe - descuento
                traslado_base = importe - descuento;

                iva = traslado_base * (((impuestos_record.amount) / 100))
                iva = round(iva,decimales)
                impuesto_acumulado = impuesto_acumulado + iva
                total = subtotal + iva
                total_acumulado = total_acumulado + total

                #ImpuestosXConcepto
                impuestosxconcepto = {
                    "traslado_base": str(traslado_base),
                    "con_importe_iva": str(iva),
                    "descripcion_impuesto": str((impuestos_record.tipo_impuesto_id.descripcion.encode('utf-8'))),
                    "tipo_tasaocuota": impuestos_record.tasa_o_cuota_id.valor_maximo,
                    "tipo_factor": impuestos_record.tipo_factor_id.tipo_factor,
                    "clave_impuesto": impuestos_record.tipo_impuesto_id.c_impuesto,
                    "tipo_impuesto":impuestos_record.traslado_retenido
                }
                impuestos.append(impuestosxconcepto)

         # ConceptosXFactura
            concepto = {
                    "con_cantidad": str(conceptos_record.quantity),
                    "con_descripcion": str(conceptos_record.name),
                    "con_unidad_clave": str(conceptos_record.product_id.clave_unidad_clave_catalogo_sat_id.c_claveunidad),
                    "con_valor_unitario": str(conceptos_record.price_subtotal/conceptos_record.quantity),
                    "con_descuento": str(descuento),
                    "con_subtotal": str(subtotal), "con_importe": str(importe),
                    "con_total": str(conceptos_record.price_total),
                    "tipo_cambio": self.currency_id.rate,
                    "con_has_impuesto":1,
                    # "no_identificacion":str((conceptos_record.product_id.default_code).encode('utf-8')),
                    # "no_identificacion":str((no_identificador).encode('utf-8')),
                    "con_clave_prod_serv": str(conceptos_record.product_id.clave_prod_catalogo_sat_id.c_claveprodserv),
                    "impuestosxconcepto": impuestos,
                    }

            if conceptos_record.no_identificacion!= None and conceptos_record.no_identificacion != False:
                concepto["no_identificacion"] = str((conceptos_record.no_identificacion));

            conceptos.append(concepto)

        # Estructura JSON para timbrar la Factura
        url = str(self.url_parte.url)+"webresources/FacturacionWS/Facturar"
        print(str(self.currency_id.rate))
        if self.origin == False:
            self.origin = "sin pedido"

        if self.observaciones == False:
            self.observaciones = ""

        data = {
        "factura": {
        "receptor_uso_cfdi": self.uso_cfdi_id.c_uso_cfdi,
        "user_odoo":usuario,
        "fac_no_orden": self.number,
        "odoo_contrasena": encrypted,
        "emisor_id" : str(self.rfc_emisor),
        "receptor": receptor,
        "fac_importe" : importe_acumulado,
        "fac_porcentaje_iva" : impuesto_acumulado,
        "fac_descuento" : descuento_acumulado,
        "fac_emisor_regimen_fiscal_key" : self.env.user.company_id.property_account_position_id.c_regimenfiscal,
        "fac_emisor_regimen_fiscal_descripcion": self.env.user.company_id.property_account_position_id.name,
        "fecha_facturacion" : self.date_invoice,
        "fac_observaciones" : self.observaciones,
        "fac_forma_pago_key" : self.forma_pago_id.c_forma_pago,
        "fac_metodo_pago_key" : self.metodo_pago_id.c_metodo_pago,
        "fac_tipo_comprobante" : "I" ,
        "fac_moneda": self.currency_id.name,
        "fac_tipo_cambio": self.currency_id.inverse_rate,
        #"fac_lugar_expedicion": self.env.user.company_id.zip,
        "conceptos" :
            conceptos,
        "destinatarios":arr_notifica

       }
    }
        if self.env.user.company_id.zip != None and self.env.user.company_id.zip != False:
            data["factura"]["fac_lugar_expedicion"] = self.env.user.company_id.zip;

        # Documentos relacionados
        if self.invoice_relacionados != None and self.invoice_relacionados != False\
                and self.tipo_de_relacion_id != False and self.tipo_de_relacion_id != None and self.tipo_de_relacion_id.c_tipo_relacion != False:
            cfdi_relacionados = []
            for documento in self.invoice_relacionados:
                if documento.uuid_documento == False or documento.uuid_documento == None or documento.uuid_documento == '':
                    raise ValidationError("Hay documentos relacionados que no cuentan con UUID")

                cfdi_relacionado = {
                   "uuid": documento.uuid_documento
                }
                cfdi_relacionados.append(cfdi_relacionado)
            data["factura"]["cfdi_relacionados"] = cfdi_relacionados;
            data["factura"]["fac_tipo_relacion"] = self.tipo_de_relacion_id.c_tipo_relacion;

        # "cfdi_relacionados": cfdi_relacionados,
        #    "fac_tipo_relacion":self.tipo_de_relacion_id.c_tipo_relacion,

        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        _logger = logging.getLogger(__name__)
        _logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        # print(response.text)
        json_data = json.loads(response.text)
        # Valida que la factura haya sido timbrada Correctamente
        if json_data['result']['success'] == 'true':
            self.state = 'timbrada'
            # En caso de recibir una respuesta positiva anexa el uuid al formulario de la factura timbrada
            self.uuid = json_data['result']['uuid']
            self.fac_id = json_data['result']['fac_id']
            self.fac_timbrada = "Timbrada"
            self.fac_folio = json_data['result']['fac_folio']
            self.fac_serie = json_data['result']['fac_serie']

            _logger = logging.getLogger(__name__)
            _logger.info('QUE HAY EN FAC_ID???  ' + self.fac_id)

            return True

        else:
            raise ValidationError(json_data['result']['message'])


    @api.multi
    def timbrar_nota_de_credito(self, nota_de_credito):

        precision = self.env['decimal.precision'].search([('name', '=', 'Product Price')])
        if precision == False or precision == None or precision.digits == None:
            raise UserError(_("No se encontró la precisión del producto"))

        decimales = precision.digits;

        self.url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])
        usuario = self.url_parte.usuario


        contrasena=self.url_parte.contrasena
        string=str(contrasena)
        #crea el algoritmo para encriptar la informacion
        algorithim=hashlib.md5()
        #encripta la informacion
        algorithim.update(string.encode('utf-8'))
        #La decodifica en formato hexadecimal
        encrypted=algorithim.hexdigest()


        conceptos = []
        receptor = {}
        if self.partner_id.nif!= False:
            receptor["NIF"] = self.partner_id.nif

        receptor["receptor_id"] = self.rfc_cliente_factura;
        receptor["compania"] = self.partner_id.name;
        if self.partner_id.street != None and self.partner_id.street != False:
            receptor["calle"] = self.partner_id.street;
        else:
            receptor["calle"] = "";

        if self.partner_id.city != None and self.partner_id.city != False:
            receptor["ciudad"] = self.partner_id.city;
        else:
            receptor["ciudad"] = "";

        if self.partner_id.email != None and self.partner_id.email != False:
            receptor["correo"] = self.partner_id.email;
        else:
            receptor["correo"] = "";

        if self.partner_id.colonia != None and self.partner_id.colonia != False:
            receptor["colonia"] = self.partner_id.colonia;
        else:
            receptor["colonia"] = "";

        if self.partner_id.zip != None and self.partner_id.zip != False:
            receptor["codigopostal"] = self.partner_id.zip;
        else:
            receptor["codigopostal"] = "";

        if self.partner_id.numero_ext != None and self.partner_id.numero_ext != False:
            receptor["numero_ext"] = self.partner_id.numero_ext;
        else:
            receptor["numero_ext"] = "";

        if self.partner_id.state_id.name != None and self.partner_id.state_id.name != False:
            receptor["estado"] = self.partner_id.state_id.name;
        else:
            receptor["estado"] = "";

        # if self.partner_id.nif!= False:
        #     receptor = {
        #     "receptor_id": self.rfc_cliente_factura,
        #     "compania":self.partner_id.name.encode('utf-8'),
        #     "calle": self.partner_id.street.encode('utf-8'),
        #     "ciudad":self.partner_id.city.encode('utf-8'),
        #     "correo":self.partner_id.email.encode('utf-8'),
        #     "colonia":self.partner_id.colonia.encode('utf-8'),
        #     "codigopostal":self.partner_id.zip,
        #     "numero_ext":self.partner_id.numero_ext,
        #     "estado":self.partner_id.state_id.name.encode('utf-8'),
        #     "NIF": self.partner_id.nif.encode('utf-8')
        # }
        # else:
        #     receptor = {
        #     "receptor_id": self.rfc_cliente_factura,
        #     "compania":self.partner_id.name.encode('utf-8'),
        #     "calle": self.partner_id.street.encode('utf-8'),
        #     "ciudad":self.partner_id.city.encode('utf-8'),
        #     "correo":self.partner_id.email.encode('utf-8'),
        #     "colonia":self.partner_id.colonia.encode('utf-8'),
        #     "codigopostal":self.partner_id.zip,
        #     "numero_ext":self.partner_id.numero_ext,
        #     "estado":self.partner_id.state_id.name.encode('utf-8'),
        # }

        # TODO add omar
        primer_inv_rel = self.env['account.invoice'].browse(self.invoice_relacionados.ids)
        primer_uuid_rel = primer_inv_rel.uuid

        cfdi_relacionados = []
        cfdi_relacionado = {
            "uuid": primer_uuid_rel  # todo omar change
        }
        cfdi_relacionados.append(cfdi_relacionado)

        descuento_acumulado = 0.0
        total_acumulado = 0.0
        importe_acumulado = 0.0
        impuesto_acumulado = 0.0


        mpuesto_retenido = 0.0

        for conceptos_record in self.invoice_line_ids:

            importe= conceptos_record.price_unit*conceptos_record.quantity
            importe_acumulado = importe_acumulado+importe
            impuestos = []
            descuento = importe*((conceptos_record.discount)/100)
            descuento_acumulado = descuento_acumulado+descuento
            subtotal = importe

            for impuestos_record in conceptos_record.invoice_line_tax_ids:

                iva = importe * (((impuestos_record.amount) / 100))
                iva = round(iva,decimales)
                impuesto_acumulado = impuesto_acumulado + iva
                total = subtotal + iva
                total_acumulado = total_acumulado + total

                #ImpuestosXConcepto
                impuestosxconcepto = {
                    "traslado_base": str(importe),
                    "con_importe_iva": str(iva),
                    "descripcion_impuesto": str((impuestos_record.tipo_impuesto_id.descripcion )),
                    "tipo_tasaocuota": impuestos_record.tasa_o_cuota_id.valor_maximo,
                    "tipo_factor": impuestos_record.tipo_factor_id.tipo_factor,
                    "clave_impuesto": impuestos_record.tipo_impuesto_id.c_impuesto,
                    "tipo_impuesto":impuestos_record.traslado_retenido
                }
                impuestos.append(impuestosxconcepto)


         # ConceptosXFactura
            concepto = {"con_cantidad": str(conceptos_record.quantity), "con_descripcion": str(conceptos_record.name ),
                    "con_unidad_clave": str(conceptos_record.product_id.clave_unidad_clave_catalogo_sat_id.c_claveunidad),
                    "con_valor_unitario": str(conceptos_record.price_unit), "con_descuento": str(descuento),
                    "con_subtotal": str(subtotal), "con_importe": str(importe),
                    "con_total": str(conceptos_record.price_subtotal), "tipo_cambio": self.currency_id.rate,
                    "con_has_impuesto":1,
                    #"no_identificacion":str((conceptos_record.product_id.default_code).encode('utf-8')),
                    #"no_identificacion":str((no_identificador).encode('utf-8')),
                    "con_clave_prod_serv": str(conceptos_record.product_id.clave_prod_catalogo_sat_id.c_claveprodserv),
                    "con_descripcion":"Nota de Credito:Referencia Factura "+str(self.number)+" con motivo de "+str(nota_de_credito),
                    "impuestosxconcepto": impuestos,
                    }

            if conceptos_record.no_identificacion!= None and conceptos_record.no_identificacion != False:
                concepto["no_identificacion"] = str((conceptos_record.no_identificacion));


            conceptos.append(concepto)
        
        #Estructura JSON para timbrar la Factura
        url = str(self.url_parte.url)+"webresources/FacturacionWS/Facturar"
        print (str(self.currency_id.rate))
        if self.origin == False:
            self.origin = "sin pedido"

        data = {
        "factura": { 
        "receptor_uso_cfdi": self.uso_cfdi_id.c_uso_cfdi,
        "user_odoo":usuario,
        "fac_no_orden": self.number,
        "odoo_contrasena": encrypted,
        "emisor_id" : str(self.rfc_emisor),
        "receptor": receptor,
        "fac_importe" : importe_acumulado,
        "fac_porcentaje_iva" : impuesto_acumulado,
        "fac_descuento" : descuento_acumulado,
        "fac_emisor_regimen_fiscal_key" : self.env.user.company_id.property_account_position_id.c_regimenfiscal,
        "fac_emisor_regimen_fiscal_descripcion": self.env.user.company_id.property_account_position_id.name,   
        "fecha_facturacion" : self.date_invoice,
        "fac_forma_pago_key" : self.forma_pago_id.c_forma_pago,
        "fac_metodo_pago_key" : self.metodo_pago_id.c_metodo_pago,
        "fac_tipo_comprobante" : "E" ,
        "cfdi_relacionados": cfdi_relacionados,
            "fac_tipo_relacion":self.tipo_de_relacion_id.c_tipo_relacion,
        "fac_moneda": self.currency_id.name,
        "fac_tipo_cambio": self.currency_id.inverse_rate,
        "fac_lugar_expedicion": self.env.user.company_id.zip,
        "conceptos" :
            conceptos
        
       }

    }
        
        headers = {
           'content-type': "application/json", 'Authorization':"Basic YWRtaW46YWRtaW4="
    }
        self._logger.info(data)

        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        json_data = json.loads(response.text)
        self._logger.info(json_data)
        #Valida que la factura haya sido timbrada Correctamente
        if json_data['result']['success']== 'true':
            self.state = 'timbrada'
            #En caso de recibir una respuesta positiva anexa el uuid al formulario de la factura timbrada
            self.uuid = json_data['result']['uuid']
            self.fac_id = json_data['result']['fac_id']
            self.fac_timbrada = "Timbrada"
        else:
            raise ValidationError(json_data['result']['message'])

    @api.multi
    def descargar_factura_pdf(self):

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])

        string=str(str(self.fac_id))
        algorithim=hashlib.md5()
        algorithim.update(string.encode("utf-8"))
        encrypted=algorithim.hexdigest()

        url_descarga_pdf = url_parte.url+self.pdf+encrypted
        return {
            'type': 'ir.actions.act_url',
            'url': url_descarga_pdf,
            'target': 'new',
        }
        
    @api.multi
    def descargar_factura_xml(self):
        
        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])

        string=str(str(self.fac_id))
        algorithim=hashlib.md5()
        algorithim.update(string.encode("utf-8"))
        encrypted=algorithim.hexdigest()

        url_descarga_xml = url_parte.url+self.xml+encrypted
        return {
            'type': 'ir.actions.act_url',
            'url': url_descarga_xml,
            'target': 'new',
        }

    @api.multi
    def validar(self):
        print("Entra a validar");
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        for invoice in self:
            #refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
            #because it's probably a double encoding of the same bill/refund
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
                    raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
        return self.write({'state': 'validate'})


        #Cambia el Estado de Borrador a Validado
        #for invoice in self:
            #refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
            #because it's probably a double encoding of the same bill/refund
        #    if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
        #        if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
        #            raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
        #return self.write({'state': 'validate'})
        #super(account_invoice, self).invoice_validate();
        #Cambia el Estado de Borrador a Validado
        #for invoice in self:
            #refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
            #because it's probably a double encoding of the same bill/refund
        #    if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
        #        if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
        #            raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))


    def cancelaFacturaNuevoProceso(self):
        self.action_cancel();
        self.state = 'cancel'

    @api.multi
    def cancelar_factura_timbrada(self):
        #Valida que no tenga algún pago con timbre
        if self.fac_timbrada == 'Timbrada':
            pagos_timbrados = self.env['account.payment'].search([('ref', '=',self.number), ('uuid', '!=','')])
            if len(pagos_timbrados) > 0:
                raise ValidationError("La factura ya tiene pagos timbrados, no se puede cancelar")


        if self.fac_timbrada == 'Timbrada':
            #Validar que no tenga pagos

            url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])
            url = str(url_parte.url)+"webresources/FacturacionWS/Cancelar"
            data = {
             "uuid": self.uuid
            }

            headers = {
               'content-type': "application/json", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }



            response = requests.request("POST", url, data=json.dumps(data), headers=headers)
            self._logger.info(response.text)
            json_data = json.loads(response.text)
            if json_data['result']['success'] == True or json_data['result']['success'] == "true":
                #self.fac_timbrada = "Timbre Cancelado"
                if "En proceso" ==json_data['result']['estatus']:
                    return 'EN_PROCESO'
                    #self.fac_timbrada = "En proceso";
                else:
                    #Cancela factura de Odoo
                    #self.action_cancel();
                    #Si se cancela sin aceptación, procesa la cancelación
                    self.fac_timbrada = "Timbre Cancelado";
                    self.cancelaFacturaNuevoProceso();
                    return 'OK'

                self.fac_estatus_cancelacion = json_data['result']['estatus']

            else:
                try:
                    raise ValidationError(json_data['result']['message'])
                finally:
                    return 'ERROR'

        @api.multi
        def action_invoice_open(self):
            # lots of duplicate calls to action_invoice_open, so we remove those already open
            #to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
            #if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft', 'validate']):
            #    raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))

            if self.state not in ['proforma2', 'draft', 'validate']:
                raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
            self.action_date_assign()
            self.action_move_create()
            return self.invoice_validate()

    #Modifico  el metodo de Validacion Original para que el estado en que termina sea validate en vez de open
    @api.multi
    def invoice_validate(self):
        if self.type:
            if self.type in ("in_invoice"):
                super(localizacion_mexicana,self).invoice_validate();


        #Sólo lo valida cuando son facturas y notas de crédito emitidas
        if self.type in ("out_invoice","out_refund"):
            # Valida los campos
            self.validar_campos()

            # Valida las lineas de Factura
            product_id = []
            for j in self.invoice_line_ids:
                product_id.append(j.product_id)
                # Valida que los impuestos asignados contengan sus correspondientes claves
                for taxs in j.invoice_line_tax_ids:
                    if taxs.tipo_impuesto_id.descripcion == False:
                        raise ValidationError(
                            "FACT00001: El impuesto %s no tiene asignada ninguna clave del Catalogo del Sat que lo identifique" % (taxs.name))
                #Valida que los productos asignados cuenten con las claves del sat asignadas
                for record_product in product_id:
                    if record_product.clave_unidad_clave_catalogo_sat_id.nombre == False:
                        raise ValidationError("FACT002: Clave de unidad de medida del producto %s no asignada" % (record_product.name))
                    else:
                        if record_product.clave_prod_catalogo_sat_id.descripcion == False:
                            raise ValidationError("FACT002: Clave de unidad de medida del producto %s no asignada" % (record_product.name))
                        # else:
                        #     if record_product.default_code == False:
                        #         raise ValidationError("FACT002: El campo (referencia interna) del producto %s no  ha sido asignada la cual servira"
                        #             " como No.Identificacion para la facturacion Electronica, usted puede asignarla dentro del modulo de inventarios en la seccion Informacion General" % (record_product.name))

            #Cambia el Estado de Borrador a Validado
            for invoice in self:
                #refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
                #because it's probably a double encoding of the same bill/refund
                if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                    if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
                        raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
            #return self.write({'state': 'validate'})

            #Factura Emitida
            if self.type == "out_invoice":
                self.timbrar_factura()

            #Nota de crédito
            if self.type == "out_refund":
                nota_de_credito_descripcion = self.name
                self.timbrar_nota_de_credito(nota_de_credito_descripcion)

    @api.multi
    def action_invoice_open_2(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        return to_open_invoices.invoice_validate_2()

    @api.multi
    def invoice_validate_2(self):
        for invoice in self:
            #refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
            #because it's probably a double encoding of the same bill/refund
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
                    raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
        return self.write({'state': 'open'})

    @api.multi
    def validar_campos(self):
        _logger = logging.getLogger(__name__)
        # if self.partner_id.country_id == False:
        #         raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: El ciente de origen extranjero %s no tiene el Pais registrado, favor de asignarlo primero" % (self.partner_id.name))

        if self.rfc_cliente_factura == False or self.rfc_cliente_factura ==  None:
                raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene ningun RFC asignado o un NIF(RFC Ventas en General), favor de asignarlo primero" % (self.partner_id.name))
        else:
            if len(self.rfc_cliente_factura) > 13:
                raise ValidationError("El RFC %s sobrepasa los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (self.rfc_cliente_factura))
            if len(self.rfc_cliente_factura) < 12:
                raise ValidationError("El RFC %s tiene menos de los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (self.rfc_cliente_factura))
            else:
                rule = re.compile(r'^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                if self.rfc_cliente_factura != 'XAXX01010100' and  not rule.search(self.rfc_cliente_factura):
                    msg = "Formato de RFC Invalido"
                    msg = msg + "El formato correcto es el siguiente:\n\n"
                    msg = msg + "-Apellido Paterno (del cual se van a utilizar las primeras 2 Letras). \n"
                    msg = msg + "-Apellido Materno (de este solo se utilizará la primera Letra).\n"
                    msg = msg + "-Nombre(s) (sin importar si tienes uno o dos nombres, solo se utilizarà la primera Letra del primer nombre).\n"
                    msg = msg + "-Fecha de Nacimiento (día, mes y año).\n"
                    msg = msg + "-Sexo (Masculino o Femenino).\n"
                    msg = msg + "-Entidad Federativa de nacimiento (Estado en el que fue registrado al nacer)."
                    raise ValidationError(msg)
        _logger.info(self.env.user.company_id.property_account_position_id.c_regimenfiscal)
        if self.env.user.company_id.property_account_position_id.c_regimenfiscal == False or self.env.user.company_id.property_account_position_id.c_regimenfiscal == None:
            raise ValidationError("La compania %s no tiene asignado ningun Regimen Fiscal, favor de asignarlo primero" % (self.env.user.company_id.name))

        # if self.partner_id.colonia == False:
        #     raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ninguna Colonia, favor de asignarlo primera" % (self.partner_id.name))

        if self.partner_id.email == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignado ningun Correo Electronico, favor de asignarlo primera" % (self.name))

        # if self.partner_id.city == False:
        #     raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ninguna Ciudad, favor de asignarlo primera" % (self.partner_id.name))

        # if self.partner_id.zip == False:
        #     raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ningun Codigo Postal, favor de asignarlo primera" % (self.partner_id.name))
        #
        # if self.partner_id.country_id.name == False:
        #     raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ningun Pais, favor de asignarlo primera" % (self.partner_id.name))
        #
        # if self.partner_id.numero_ext == False:
        #     raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ningun No Exterior, favor de asignarlo primera" % (self.name))

        #Validacionciones Atributos de Factura
        if self.forma_pago_id.descripcion == False:
            raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar: La forma de pago no ha sido asignada")

        if self.metodo_pago_id.descripcion == False:
            raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar:El Metodo de Pago no ha sido asignada")

        # if self.codigo_postal_id.c_estado == False:
        #     raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar: xpedicion no ha sido asignada")
        
        if self.uso_cfdi_id.descripcion == False:
            raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar: el Uso de CFDI no ha sido asignado")

        #Valida los datos Fiscales de la Compañia
        if self.env.user.company_id.company_registry == False:
            raise ValidationError("Error de Validacion : La compania %s no tiene ningun RFC asignado, favor de asignarlo primero" % (self.env.user.company_id.name))

        # if self.partner_id.cfdi == False:
        #     raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene activado el campo CFDI que permite Facturar" % (self.partner_id.name))

        # if self.invoice_line_ids != False and len(self.invoice_line_ids)>0:
        #     for product in self.invoice_line_ids:
        #         if product.no_identificacion == False or product.no_identificacion == None or product.no_identificacion == '':
        #             print 'producto'
        #             print product.product_id.name
        #             raise ValidationError("Favor de introducir el No. Identificador para el producto %s " % (product.product_id.name))

    @api.multi
    def empezar_a_pagar(self):
        self.state='open'
    
    #Me obtiene el ultimo pago realizado en la factura
    @api.multi
    def Obtener_Valores_de_los_Pagos(self):
        pagos = []
        for fac_pagos in self.payment_ids:
            pagos.append(fac_pagos.amount)
            
        raise ValidationError('result %s' % pagos[0])


    # @api.one
    # def _get_outstanding_info_JSON(self):
    #     self.outstanding_credits_debits_widget = json.dumps(False)
    #     if self.state == 'open':
    #         domain = [('account_id', '=', self.account_id.id), ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id), ('reconciled', '=', False), ('state','!=','canceled'), ('amount_residual', '!=', 0.0)]
    #         if self.type in ('out_invoice', 'in_refund'):
    #             domain.extend([('credit', '>', 0), ('debit', '=', 0)])
    #             type_payment = _('Outstanding credits')
    #         else:
    #             domain.extend([('credit', '=', 0), ('debit', '>', 0)])
    #             type_payment = _('Outstanding debits')
    #         info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
    #         lines = self.env['account.move.line'].search(domain)
    #         currency_id = self.currency_id
    #         if len(lines) != 0:
    #             for line in lines:
    #                 # get the outstanding residual value in invoice currency
    #                 if line.currency_id and line.currency_id == self.currency_id:
    #                     amount_to_show = abs(line.amount_residual_currency)
    #                 else:
    #                     amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(abs(line.amount_residual), self.currency_id)
    #                 if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
    #                     continue
    #                 info['content'].append({
    #                     'journal_name': line.ref or line.move_id.name,
    #                     'amount': amount_to_show,
    #                     'currency': currency_id.symbol,
    #                     'id': line.id,
    #                     'position': currency_id.position,
    #                     'digits': [69, self.currency_id.decimal_places],
    #                 })
    #             info['title'] = type_payment
    #             self.outstanding_credits_debits_widget = json.dumps(info)
    #             self.has_outstanding = True


    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': []}
            currency_id = self.currency_id
            for payment in self.payment_move_line_ids:
                payment_currency_id = False
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in payment.matched_debit_ids]) and payment.matched_debit_ids[0].currency_id or False
                elif self.type in ('in_invoice', 'out_refund'):
                    amount = sum([p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                    if payment.matched_credit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in payment.matched_credit_ids]) and payment.matched_credit_ids[0].currency_id or False
                # get the payment value in invoice currency
                print(payment_currency_id)
                if payment_currency_id and payment_currency_id == self.currency_id:
                    amount_to_show = amount_currency
                else:
                    print( self.currency_id)
                    amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount, self.currency_id)
                    print( amount_to_show)
                if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                    continue
                payment_ref = payment.move_id.name
                if payment.move_id.ref:
                    payment_ref += ' (' + payment.move_id.ref + ')'
                info['content'].append({
                    'name': payment.name,
                    'journal_name': payment.journal_id.name,
                    'amount': amount_to_show,
                    'currency': currency_id.symbol,
                    'digits': [69, currency_id.decimal_places],
                    'position': currency_id.position,
                    'date': payment.date,
                    'payment_id': payment.id,
                    'payment_pago_id': payment.payment_id.id,
                    'move_id': payment.move_id.id,
                    'ref': payment_ref,
                })
            self.payments_widget = json.dumps(info)

# todo add omar
    is_created = fields.Boolean()
    is_nota_de_credito = fields.Boolean()

    # todo add omar
    @api.model
    def create(self, vals):
        vals['is_created'] = True

        prod_univ = False

        if vals.get('refund_invoice_id'):
            vals['is_nota_de_credito'] = True
            prod_univ = self.env['product.product'].search([('default_code', '=', 'NOTA_CR')])            # fixme pendeiente crear producto universal

            if not prod_univ:
                raise exceptions.ValidationError('No existe el Producto con codigo "NOTA_CR" (Necesario para el concepto unitario de la nota de credito) - Actualize el modulo Sft-Facturacion para regenerarlo ')


        invoice_created = super(localizacion_mexicana, self).create(vals)

        if invoice_created.is_nota_de_credito:
            fact_rel = self.env['account.invoice'].browse(invoice_created.refund_invoice_id.id)
            lineas = fact_rel.invoice_line_ids
            # fact_rel_lineas = self.env['account.invoice.line'].browse(fact_rel.invoice_line_ids)

            # clave_univ_id = self['cfdi.clave_unidad'].search([('c_claveunidad', '=', 'ACT')]).id


            # elimina las lineas individuales de la nota actual
            invoice_created.invoice_line_ids.write({'invoice_id': False})

            invoice_created.invoice_line_ids.unlink()
            invoice_created.tax_line_ids.unlink()


            esqueleto_linea = fact_rel.invoice_line_ids[0].copy()
            #esqueleto_impuestos = fact_rel.tax_line_ids[0].copy()

            esqueleto_linea.write({'name': invoice_created.name,
                                   'invoice_id': invoice_created.id,
                                   'product_id': prod_univ.id,
                                   'no_identificacion': '01',
                                   #  'price_unit': monto_recuperado,
                                   'quantity': 1,
                                   'invoice_line_tax_ids': prod_univ.product_tmpl_id.taxes_id.ids})  # faltan impuestos



            #account.invoice.tax

            #esqueleto_impuestos.write({'invoice_id': invoice_created.id,
            #                           'tax_id': prod_univ.product_tmpl_id.taxes_id})

            '''
            linea_unica = self.env['account.invoice.line'].create({'name': 'Descripcion default',
                                                               'invoice_id': invoice_created.id,
                                                               'product_id': id_prod_univ,
                                                               'price_unit': precio_universal})
            '''

            id_tipo_relacion = self.env['cfdi.tipo_relacion'].search([('c_tipo_relacion', '=', '01')]).id
            fact_rel_ids = self.env['account.invoice'].browse(invoice_created.refund_invoice_id.id).ids
            fact_rel_ids = fact_rel_ids
            # aqui poner TODA la informacion relacionada a la factura
            invoice_created.write({'rfc_cliente_factura': fact_rel.rfc_cliente_factura,
                                   'forma_pago_id': fact_rel.forma_pago_id.id,
                                   'metodo_pago_id': fact_rel.metodo_pago_id.id,
                                   'uso_cfdi_id': fact_rel.uso_cfdi_id.id,
                                   'payment_term_id': fact_rel.payment_term_id.id,
                                   'tipo_de_relacion_id': id_tipo_relacion,
                                   'invoice_relacionados': [[4, fact_rel.id]],
                                  # 'tax_line_ids': (0, 0, {'account_id':invoice_created.account_id.id, 'tax_id': prod_univ.product_tmpl_id.taxes_id.ids[0], 'name': 'generico'})
                                   })

            taxes_model = self.env['account.invoice.tax']

            taxes_producto = prod_univ.product_tmpl_id.taxes_id

            '''for tax in prod_univ.product_tmpl_id.taxes_id:

                esqueleto_impuestos = fact_rel.tax_line_ids[0].copy()
                esqueleto_impuestos.write({'invoice_id': invoice_created.id,
                                           'account_id': invoice_created.account_id.id,
                                           'tax_id':tax.id})  # faltan impuestos


                taxes_model.create({'invoice_id': invoice_created.id,
                                    'account_id':invoice_created.account_id.id,
                                    'tax_id': tax.id,
                                    'name':''})
            '''
            invoice_created._onchange_invoice_line_ids()

            invoice_created._compute_amount()

            #
            self.env['account.invoice.docto'].create({'invoice_relacionado_id': invoice_created.id,
                                                      'invoice_id': invoice_created.id})

        return invoice_created


class AccountInvoiceDocto(models.Model):
    _name = 'account.invoice.docto'

    _logger = logging.getLogger(__name__)

    invoice_id = fields.Many2one('account.invoice', string="Factura")
    partner_id = fields.Many2one('res.partner', related='invoice_id')
    invoice_relacionado_id = fields.Many2one('account.invoice', string="Factura", required=True)
    uuid_documento = fields.Char("UUID", compute="_computeDocumento")

    @api.model
    @api.depends('invoice_id')
    @api.one
    def _computeDocumento(self):
        for linea in self:
            for factura in linea.invoice_relacionado_id:
                linea.uuid_documento = factura.uuid;


#Agrega los campos al formulario de los impuestos para asignar las claves de Sat
class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    tipo_impuesto_id = fields.Many2one('cfdi.impuestos',string='Tipo de Impuesto')
    tipo_factor_id = fields.Many2one('cfdi.tipo_factor', string='Tipo Factor')
    tasa_o_cuota_id = fields.Many2one('cfdi.tasa_cuota',string='Tasa o cuota')
    traslado_retenido = fields.Selection([("TRAS","Trasladado"),("RET","Retención")],'Tipo de impuesto')
        
# "emisor_id": "ACO560518KW7",
# #"receptor_id": "IAMJ841217KMA" ,


#TODO add omar
class CreacionAutoTemplate(models.Model):
    _name = 'autocreate.producto.nota.credito'

    # todo add omar
    @api.model_cr
    def init(self):
        id_serv_prod_str = self.env['cfdi.clave_prod_serv'].search([('c_claveprodserv', '=', '84111506')]).id
        id_unidad_str = self.env['cfdi.clave_unidad'].search([('c_claveunidad', '=', 'ACT')]).id

        existe_template_universal = self.env['product.template'].search([('default_code', '=', 'NOTA_CR')], count=True)

        if id_serv_prod_str and id_unidad_str:
            if existe_template_universal == 0:
                prod_univ_created = self.env['product.template']
                prod_univ_created.create({'name': 'Servicios de facturacion',
                                          'type': 'service',
                                          'categ_id': '1',
                                          'clave_prod_catalogo_sat_id': str(id_serv_prod_str),
                                          'clave_unidad_clave_catalogo_sat_id': str(id_unidad_str),
                                          'default_code': 'NOTA_CR'})
