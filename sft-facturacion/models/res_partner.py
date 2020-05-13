# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import models, fields, api
import re

#Agrega el campo RFC al formulario de Clientes y Proveedores
class RFCClientes(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    #TODO add omar
    mis_cuentas = fields.One2many('cuenta.bancaria.sft', 'partner_id')

    is_a_user = fields.Boolean(string='Es un usuario?',default=False)
    #rfc_cliente = fields.Char(string='RFC',size=13)
    colonia = fields.Char(string='Colonia')
    numero_int = fields.Char(string='Numero Int')
    numero_ext = fields.Char(string='Numero Exterior')
    nif = fields.Char(string='NIF EXTRA')
    municipio = fields.Char(string='Municipio')
    company_type = fields.Selection([
            ('person','Persona Fisica'),
            ('company', 'Persona Moral'),
        ], index=True, default='person',
        track_visibility='onchange', copy=False)
    #Los Siguientes campos son relacionales extra que solo si estan configurados
    #Se cargan en la Factura de Venta al Seleccionar el cliente.
    #Por tanto no son obligatorios.
    metodo_pago_id = fields.Many2one('cfdi.metodo_pago', string='Metodo de pago')
    uso_cfdi_id = fields.Many2one('cfdi.uso_cfdi', string='Uso CFDI')


    #invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines', oldname='invoice_line',
    #    readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    partner_notifica_ids = fields.One2many('res.partner.notifica', 'partner_id', string='Notificaciones', copy=False)

    # @api.constrains('colonia')
    # def validar_Municipio(self):
    #     if self.customer== True:
    #         if self.cfdi == True:
    #             if self.municipio == False:
    #                     raise ValidationError("Error de Validacion : El cliente %s no tiene asignado ningun municipio, favor de asignarlo primera" % (self.name))

    @api.constrains('vat','country_id')
    def validar_RFC(self):
        for record in self:
            if record.customer== True and record.is_company == True:
                if record.vat == False:
                    if record.nif == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene ningun RFC asignado, favor de asignarlo primero" % (record.name))
                else:
                    if record.is_company == True:
                        #Valida RFC en base al patron de una persona Moral
                        if record.vat != False and len(record.vat)!=12:
                            raise ValidationError("El RFC %s no tiene la logitud de 12 caracteres para personas Morales que establece el sat" % (record.vat))
                        else:
                            patron_rfc = re.compile(r'^([A-ZÑ\x26]{3}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                            if not patron_rfc.search(record.vat):
                                msg = "Formato RFC de Persona Moral Incorrecto"
                                raise ValidationError(msg)
                    else:
                        #Valida el RFC en base al patron de una Persona Fisica
                        if record.vat != False and len(record.vat)!=13:
                            raise ValidationError("El RFC %s no tiene la logitud de 13 caracteres para personas Fisicas que establece el sat" % (record.vat))
                        else:
                            patron_rfc = re.compile(r'^([A-ZÑ\x26]{4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                            if not patron_rfc.search(record.vat):
                                msg = "Formato RFC de Persona Fisica Incorrecto"
                                raise ValidationError(msg)

    @api.constrains('nif')
    def validar_NIF(self):
        for record in self:
            if record.customer== True:
                if record.nif == False:
                    if record.vat == False:
                        raise ValidationError("Error de Validacion : El cliente de origen extranjero %s no tiene el NIF registrado, favor de asignarlo primero" % (record.name))

    # @api.constrains('colonia')
    # def validar_Colonia(self):
    #     if self.customer== True:
    #         if self.cfdi == True:
    #             if self.colonia == False:
    #                     raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ninguna Colonia, favor de asignarlo primera" % (self.name))

    @api.constrains('email')
    def validar_Email(self):
        for record in self:
            if record.customer== True:
                if record.email == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignado ningun Correo Electronico, favor de asignarlo primera" % (record.name))

    # @api.constrains('city')
    # def validar_Ciudad(self):
    #     if self.customer== True:
    #         if self.cfdi == True:
    #             if self.city == False:
    #                     raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ninguna Ciudad, favor de asignarlo primera" % (self.name))

    @api.constrains('zip')
    def validar_Codigo_Postal(self):
        for record in self:
            if record.customer== True:
                if record.zip == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ningun Codigo Postal, favor de asignarlo primera" % (record.name))

    # @api.constrains('country_id')
    # def validar_Pais(self):
    #     if self.customer== True:
    #         if self.cfdi == True:
    #             if self.country_id.name == False:
    #                     raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ningun Pais, favor de asignarlo primera" % (self.name))
    #
    # @api.constrains('numero_ext')
    # def validar_No_Exterior(self):
    #     if self.customer== True:
    #         if self.cfdi == True:
    #             if self.numero_ext == False:
    #                     raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ningun No Exterior, favor de asignarlo primera" % (self.name))
    #
    # @api.constrains('state_id')
    # def validar_No_Exterior(self):
    #     if self.customer== True:
    #         if self.cfdi == True:
    #             if self.state_id.name == False:
    #                     raise ValidationError("Error de Validacion : El cliente %s no tiene asignad ningun Estado, favor de asignarlo primero" % (self.name))


class NotificaCFDI(models.Model):
    _name = 'res.partner.notifica'

    correo = fields.Char(string='Correo', required=True)
    #partner_id = fields.Many2one('account.invoice', string='Invoice Reference',
    #    ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Cliente Ref', ondelete='cascade')

    # @api.constrains('correo')
    # def correo_validacion(self):
    #     """ make sure nid starts with capital letter, followed by 12 numbers and ends with a capital letter"""
    #     for rec in self:
    #         if not re.match(r"^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$]$", rec.correo):
    #             raise ValidationError("Error de Validacion : El correo (%s) no tiene el formato adecuado" % (rec.correo))
