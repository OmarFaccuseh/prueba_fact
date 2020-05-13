# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class Aduanas(models.Model):
    _name = 'cfdi.aduanas'
    _description = u"Catálogo de aduanas (tomado del anexo 22, apéndice I de la RGCE 2015)."

    _logger = logging.getLogger(__name__)
 #   _rec_name = "descripcion"

    c_aduana = fields.Integer(string='c_Aduana', required=True)
    descripcion = fields.Char(string='Descripcion')


