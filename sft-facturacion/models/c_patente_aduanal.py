# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PatenteAduanal(models.Model):
    _name = 'cfdi.patente_aduanal'

    c_patente_aduanal = fields.Integer(string='c_Patente Aduanal')
    fecha_inicio_vigencia = fields.Date(string='Inicio de Vigencia')
    fecha_fin_vigencia = fields.Date(string='Fin de Vigencia')
