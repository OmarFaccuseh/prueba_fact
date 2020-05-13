# -*- coding: utf-8 -*-
import re
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import models, fields, api

#Modifica el Label de la configuracion de la compania
class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    property_account_position_id = fields.Many2one('account.fiscal.position',string='Regimen Fiscal')

    @api.constrains('company_registry')
    def ValidarRegimenFiscal(self):
        for record in self:
            if record.property_account_position_id.c_regimenfiscal == False or record.property_account_position_id.c_regimenfiscal == None:
                raise ValidationError("La compania %s no tiene asignado ningun Regimen Fiscal, favor de asignarlo primero" % (record.name))

    @api.constrains('company_registry')
    def ValidarFormatoRFC(self):
        for record in self:
            if record.company_registry == False:
                if record.country_id.code == 'MX':
                    raise ValidationError("Error de Validacion : La compania %s no tiene ningun RFC asignado, favor de asignarlo primero" % (record.name))
        else:
            if record.company_registry != False and len(record.company_registry) >13:
                raise ValidationError("El RFC %s sobrepasa los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (record.company_registry))
            if record.company_registry != False and len(record.company_registry) < 12:
                raise ValidationError("El RFC %s tiene menos de los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (record.company_registry))
            else:
                rule = re.compile(r'^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                if not rule.search(record.company_registry):
                    msg = "Formato de RFC Invalido"
                    msg = msg+"El formato correcto es el siguiente:\n\n"
                    msg = msg+"-Apellido Paterno (del cual se van a utilizar las primeras 2 Letras). \n"
                    msg = msg+"-Apellido Materno (de este solo se utilizará la primera Letra).\n"
                    msg=  msg+"-Nombre(s) (sin importar si tienes uno o dos nombres, solo se utilizarà la primera Letra del primer nombre).\n"
                    msg = msg+"-Fecha de Nacimiento (día, mes y año).\n"
                    msg=  msg+"-Sexo (Masculino o Femenino).\n"
                    msg = msg+"-Entidad Federativa de nacimiento (Estado en el que fue registrado al nacer)."
                    raise ValidationError(msg)
    
    @api.onchange('street','company_registry','city','state_id','country_id','zip')
    def Actualizar_Datos_fiscales_de_la_compania_en_las_Facturas_de_Venta(self):

        # lugar_de_expedicion = self.env['cfdi.codigo_postal'].search([('c_codigopostal', '=',self.zip)])
        # if lugar_de_expedicion.id == False:
        #     raise ValidationError("Favor de Revisar el Codigo Postal ya que no se encuentra en el catalogo del sat")

        self._cr.execute("update account_invoice "
                        " set compania_calle= %s,"
                        "  compania_ciudad = %s, "
                        "  compania_estado = %s, "
                        "  rfc_emisor = %s, "
                        "  compania_pais = %s "
                        "  where state = 'draft' and type = 'out_invoice' ", (self.street, self.city, self.state_id.name, self.company_registry, self.country_id.name, ) )


        # invoices = self.env['account.invoice'].search([('state', '=','draft')])
        # for invoice in invoices:
        #     invoice.write({'compania_calle': self.street})
        #     invoice.write({'compania_ciudad': self.city})
        #
        #     invoice.write({'codigo_postal_id': lugar_de_expedicion.id})
        #     invoice.write({'compania_estado': self.state_id.name})
        #     invoice.write({'rfc_emisor': self.company_registry})
        #     invoice.write({'compania_pais': self.country_id.name})

