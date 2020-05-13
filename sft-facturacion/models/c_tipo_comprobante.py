# -*- coding: utf-8 -*-

from odoo import models, fields, api

class TipoComprobante(models.Model):
    _name = 'cfdi.tipo_comprobante'
    _rec_name = "descripcion"

    c_tipo_de_comprobante = fields.Char(string='c_TipoDeComprobante')
    descripcion = fields.Char(string='Descripción')
    valor_maximo1 = fields.Char(string='Valor Maximo 1')
    valor_maximo2 = fields.Char(string='Valor Maximo 2')
    fecha_inicio_vigencia = fields.Char(string='Fecha inicio de vigencia')
    fecha_fin_vigencia = fields.Char(string='Fecha fin de vigencia')
