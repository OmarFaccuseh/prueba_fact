# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class MetodoPago(models.Model):
    _name = 'cfdi.metodo_pago'
    _rec_name = "descripcion"

    _logger = logging.getLogger(__name__)

    c_metodo_pago = fields.Char("c Metodo Pago")	
    descripcion = fields.Char("Descripcion")	
    fecha_inicio_vigencia = fields.Date(string='Fecha de inicio de Vigencia')
    fecha_fin_vigencia = fields.Date(string='Fecha de Fin de Vigencia')

    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerMetodoPago"
        data = {};
        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_metodo_pago = self.env['cfdi.metodo_pago']
        if json_data["result"]["success"] == True:
            arr_metodo = json_data["result"]["metodopago"];
            for ws_metodo in arr_metodo:
                None;
                arr_uso = obj_metodo_pago.search([("c_metodo_pago","=",ws_metodo["met_clave"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];

                metodo["c_metodo_pago"] = ws_metodo["met_clave"];
                metodo["descripcion"] = ws_metodo["met_descripcion"];


                if len(arr_uso)>0:
                    obj_metodo_pago.update(metodo);
                else:
                    obj_metodo_pago.create(metodo);

        else:
            None;
