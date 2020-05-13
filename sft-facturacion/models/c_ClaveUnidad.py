# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
import requests
import json

class ClaveUnidad(models.Model):
    _name = 'cfdi.clave_unidad'
    _rec_name = 'nombre'
    _description =u'Catálogo de unidades de medida para los conceptos en el CFDI. Version 2.0'

    _logger = logging.getLogger(__name__)

    c_claveunidad = fields.Char(string="c_ClaveUnidad", required=True)	
    nombre = fields.Char()
    descripcion = fields.Char()
    nota = fields.Text()
    fecha_de_inicio_de_vigencia = fields.Date(string='Inicio de Vigencia')	
    fecha_de_fin_de_vigencia = fields.Date(string='Fin de Vigencia')
    simbolo = fields.Char()

    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerUnidadMedida"
        data = {};
        #self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        #self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_unidad = self.env['cfdi.clave_unidad']
        if json_data["resultado"]["success"] == True:
            arr_unidades = json_data["resultado"]["unidad_medida"];
            for ws_unidad in arr_unidades:
                None;
                arr_uso = obj_unidad.search([("c_claveunidad","=",ws_unidad["uni_clave"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];

                metodo["c_claveunidad"] = ws_unidad["uni_clave"];
                metodo["nombre"] = ws_unidad["uni_nombre"];
                if hasattr(ws_unidad,"uni_descripcion"):
                    metodo["descripcion"] = ws_unidad["uni_descripcion"];
                #metodo["nota"] = ws_producto["prs_clave"];
                #metodo["fecha_de_inicio_de_vigencia"] = ws_producto["prs_clave"];
                #metodo["fecha_de_fin_de_vigencia"] = ws_producto["prs_clave"];
                if hasattr(ws_unidad, "uni_simbolo"):
                    metodo["simbolo"] = ws_unidad["uni_simbolo"];



                if len(arr_uso)>0:
                    obj_unidad.update(metodo);
                else:
                    obj_unidad.create(metodo);

        else:
            None;
