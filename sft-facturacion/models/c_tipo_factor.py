# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class TipoFactor(models.Model):
    _name = 'cfdi.tipo_factor'
    _rec_name = "tipo_factor"

    tipo_factor = fields.Char(string='Tipo de Factor')
    tipo_id = fields.Integer(string="ID WS")

    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerTipoFactor"
        data = {};
        #self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        #self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_tipo_factor = self.env['cfdi.tipo_factor']
        if json_data["resultado"]["success"] == True:
            arr_tipos = json_data["resultado"]["tipos"];
            for ws_tipo in arr_tipos:
                None;
                arr_uso = obj_tipo_factor.search([("tipo_id","=",ws_tipo["tif_id"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];

                metodo["tipo_id"] = ws_tipo["tif_id"];
                metodo["tipo_factor"] = ws_tipo["tif_desc"];



                if len(arr_uso)>0:
                    obj_tipo_factor.update(metodo);
                else:
                    obj_tipo_factor.create(metodo);

        else:
            None;
