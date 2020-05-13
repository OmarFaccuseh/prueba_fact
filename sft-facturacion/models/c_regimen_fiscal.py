# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class RegimenFiscal(models.Model):
    _name = 'account.fiscal.position'
    _inherit = "account.fiscal.position"

    _logger = logging.getLogger(__name__)

    c_regimenfiscal = fields.Char(string='c_RegimenFiscal') 	
    #descripcion = fields.Char(string='Descripción')
    fisica = fields.Char(string='Se aplica a persona Física')
    moral = fields.Char(string='Se aplica a Persona Moral')	
    fecha_inicio_vigencia = fields.Date(string='Fecha de inicio de vigencia')	
    fecha_fin_vigencia = fields.Date(string='Fecha de fin de vigencia')


    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerRegimenFiscal"
        data = {};
        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_regimen = self.env['account.fiscal.position']
        if json_data["result"]["success"] == True:
            arr_regimen = json_data["result"]["regimenfiscal"];
            for ws_regimen in arr_regimen:
                None;
                arr_uso = obj_regimen.search([("c_regimenfiscal","=",ws_regimen["ref_clave"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];
                else:
                    #arr_uso = obj_regimen.search([("name","ilike",ws_regimen["ref_descripcion"])]);
                    arr_uso = obj_regimen.search([]);
                    for uso_tmp in arr_uso:
                        if ws_regimen["ref_descripcion"] in uso_tmp["name"]:
                            metodo = arr_uso[0];
                            break;

                metodo["c_regimenfiscal"] = ws_regimen["ref_clave"];
                metodo["fisica"] = ws_regimen["ref_fisica"];
                metodo["moral"] = ws_regimen["ref_moral"];
                metodo["name"] = ws_regimen["ref_descripcion"];
                metodo["fecha_inicio_vigencia"] = ws_regimen["ref_inicio_vigencia"];
                metodo["fecha_fin_vigencia"] = ws_regimen["ref_fin_vigencia"];


                if len(arr_uso)>0:
                    obj_regimen.update(metodo);
                else:
                    obj_regimen.create(metodo);

        else:
            None;
