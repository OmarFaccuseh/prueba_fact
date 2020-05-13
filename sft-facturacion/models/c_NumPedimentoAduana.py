# -*- coding: utf-8 -*-

from odoo import models, fields, api

class NumPedimentoAduana(models.Model):
    _name = 'cfdi.num_pedimento_aduana'
    _rec_name = "patente"

    c_aduana = fields.Integer(string='c_aduana')	
    patente = fields.Integer(string='patente')
    ejercicio = fields.Integer(string='ejercicio')
    cantidad = fields.Integer(string='cantidad')
    fecha_inicio_vigencia = fields.Date(string="Inicio de Vigencia")
    fecha_fin_vigencia = fields.Date(string='Fin de Vigencia')
