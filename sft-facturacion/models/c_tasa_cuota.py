# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
import requests
import json

class TasaCuota(models.Model):
    _name = 'cfdi.tasa_cuota'
    _rec_name = "valor_maximo"

    _logger = logging.getLogger(__name__)

    taz_id  = fields.Integer(string="ID de la taza")
    rango_o_fijo = fields.Char(string='Rango o Fijo')
    valor_minimo  = fields.Float(string='Valor mínimo')	
    valor_maximo = fields.Float(string='Valor máximo')
    impuesto = fields.Char(string='Impuesto')
    factor = fields.Char(string='Factor')
    traslado = fields.Char(string='Traslado')
    retencion = fields.Char(string='Retención')
    fecha_inicio_vigencia = fields.Char(string='Fecha inicio de vigencia')
    fecha_fin_vigencia = fields.Char(string='Fecha fin de vigencia')


    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerTasaoCuota"
        data = {};
        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_tasa_cuota = self.env['cfdi.tasa_cuota']
        if json_data["result"]["success"] == True:
            arr_tasa = json_data["result"]["tasaocuota"];
            for ws_tasa in arr_tasa:
                None;
                arr_uso = obj_tasa_cuota.search([("taz_id","=",ws_tasa["taz_id"])]);
                tasa = {};
                if len(arr_uso)>0:
                    tasa = arr_uso[0];

                tasa["taz_id"] = ws_tasa["taz_id"];
                tasa["rango_o_fijo"] = ws_tasa["taz_tipo"];
                tasa["valor_minimo"] = ws_tasa["taz_valor_minimo"];
                tasa["valor_maximo"] = ws_tasa["taz_valor_maximo"];
                tasa["impuesto"] = ws_tasa["taz_impuesto"];
                tasa["factor"] = ws_tasa["taz_factor"];
                tasa["traslado"] = ws_tasa["taz_trasladado"];
                tasa["retencion"] = ws_tasa["taz_retencion"];
                #tasa["fecha_inicio_vigencia"] = uso_cfdi["uso_clave"];
                #tasa["fecha_fin_vigencia"] = uso_cfdi["uso_clave"];


                if len(arr_uso)>0:
                    obj_tasa_cuota.update(tasa);
                else:
                    obj_tasa_cuota.create(tasa);

        else:
            None;
