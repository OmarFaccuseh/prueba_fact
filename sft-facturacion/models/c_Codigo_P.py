# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CodigoPostal(models.Model):
    _name = 'cfdi.codigo_postal'
    _rec_name = "c_codigopostal"

    c_codigopostal = fields.Char()	
    c_estado = fields.Char()	
    c_municipio	= fields.Integer()
    c_localidad = fields.Integer()

    @api.multi
    def name_get(self):
        res = []
        for codigo in self:
            codigos_postales = u'%s %s' % (codigo.c_codigopostal, codigo.c_estado)
            res.append((codigo.id, codigos_postales))
        return res


