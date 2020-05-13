# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class Impuestos(models.Model):
    _name = 'cfdi.impuestos'
    _rec_name = "descripcion"

    c_impuesto = fields.Char(string='c_Impuesto')
    descripcion = fields.Char(string='Descripción')
    retencion = fields.Char(string='Retención')
    traslado = fields.Char(string='Traslado')
    local_o_federal = fields.Char(string='Local o federal')
    entidad_en_quien_se_aplica = fields.Char(string='Entidad en la que aplica')


    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerImpuestos"
        data = {};
        #self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        #self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_impuesto = self.env['cfdi.impuestos']
        if json_data["resultado"]["success"] == True:
            arr_impuestos = json_data["resultado"]["impuestos"];
            for ws_impuesto in arr_impuestos:
                None;
                arr_uso = obj_impuesto.search([("c_impuesto","=",ws_impuesto["imp_clave"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];

                metodo["c_impuesto"] = ws_impuesto["imp_clave"];
                metodo["descripcion"] = ws_impuesto["imp_descripcion"];
                metodo["retencion"] = ws_impuesto["imp_retencion"];
                metodo["traslado"] = ws_impuesto["imp_traslado"];
                metodo["local_o_federal"] = ws_impuesto["imp_local_federal"];
                metodo["entidad_en_quien_se_aplica"] = ws_impuesto["imp_entidad_aplica"];



                if len(arr_uso)>0:
                    obj_impuesto.update(metodo);
                else:
                    obj_impuesto.create(metodo);

        else:
            None;
