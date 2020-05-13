# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class UsoCFDI(models.Model):
    _name = 'cfdi.uso_cfdi'
    _rec_name = "descripcion"

    _logger = logging.getLogger(__name__)

    c_uso_cfdi = fields.Char(string='c_UsoCFDI')	
    descripcion = fields.Char(string='Descripción')
    fisica = fields.Char(string='Física')
    moral = fields.Char(string='Moral')
    fecha_inicio_vigencia = fields.Date(string='Fecha inicio de vigencia')
    fecha_fin_vigencia = fields.Date(string='Fecha fin de vigencia')


    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerUsoCfdi"
        data = {};
        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_uso_cfdi = self.env['cfdi.uso_cfdi']
        if json_data["result"]["success"] == True:
            arr_uso_cfdi = json_data["result"]["usocfdi"];
            for uso_cfdi in arr_uso_cfdi:
                None;
                arr_uso = obj_uso_cfdi.search([("c_uso_cfdi","=",uso_cfdi["uso_clave"])]);
                usoCFDI = {};
                if len(arr_uso)>0:
                    usoCFDI = arr_uso[0];

                usoCFDI["c_uso_cfdi"] = uso_cfdi["uso_clave"];
                usoCFDI["descripcion"] = uso_cfdi["uso_descripcion"];
                usoCFDI["fisica"] = uso_cfdi["uso_fisica"];
                usoCFDI["moral"] = uso_cfdi["uso_moral"];
                usoCFDI["fecha_inicio_vigencia"] = uso_cfdi["uso_inicio_vigencia"];
                usoCFDI["fecha_fin_vigencia"] = uso_cfdi["uso_fin_vigencia"];

                if len(arr_uso)>0:
                    obj_uso_cfdi.update(usoCFDI);
                else:
                    obj_uso_cfdi.create(usoCFDI);

        else:
            None;
