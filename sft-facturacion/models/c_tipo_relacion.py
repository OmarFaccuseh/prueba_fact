# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class TipoRelacion(models.Model):
    _name = 'cfdi.tipo_relacion'
    _rec_name = "descripcion"

    c_tipo_relacion = fields.Char(string='c_TipoRelacion')
    descripcion = fields.Char(string='Descripción')
    fecha_inicio_vigencia = fields.Date(string='Fecha inicio de vigencia')
    fecha_fin_vigencia = fields.Date(string='Fecha fin de vigencial')

    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerTipoRelacion"
        data = {};
        #self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        #self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_tipo = self.env['cfdi.tipo_relacion']
        if json_data["resultado"]["success"] == True:
            arr_tipos = json_data["resultado"]["tipo_relacion"];
            for ws_tipo in arr_tipos:
                None;
                arr_uso = obj_tipo.search([("c_tipo_relacion","=",ws_tipo["tir_clave"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];

                metodo["c_tipo_relacion"] = ws_tipo["tir_clave"];
                metodo["descripcion"] = ws_tipo["tir_descripcion"];
                if "tir_inicio_vigencia" in ws_tipo:
                    metodo["fecha_inicio_vigencia"] = ws_tipo["tir_inicio_vigencia"];

                if "tir_fin_vigencia" in ws_tipo:
                    metodo["fecha_fin_vigencia"] = ws_tipo["tir_fin_vigencia"];



                if len(arr_uso)>0:
                    obj_tipo.update(metodo);
                else:
                    obj_tipo.create(metodo);

        else:
            None;
