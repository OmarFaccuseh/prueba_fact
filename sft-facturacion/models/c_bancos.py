# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class Aduanas(models.Model):
    _name = 'cfdi.bancos'
    _description = u"Catálogo de aduanas (tomado del anexo 22, apéndice I de la RGCE 2015)."
    _rec_name = "c_nombre"

    _logger = logging.getLogger(__name__)

    c_nombre = fields.Char(string='Nombre del Banco', required=True)
    rfc_banco = fields.Char(string='RFC Institucion Bancaria')
    clave_institucion_financiera = fields.Char(string='Clave Institucion Financiera')

    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerBancos"
        data = {};
        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_banco = self.env['cfdi.bancos']
        if json_data["resultado"]["success"] == True:
            arr_bancos = json_data["resultado"]["banco"];
            for uso_cfdi in arr_bancos:
                None;
                arr_uso = obj_banco.search([("clave_institucion_financiera","=",uso_cfdi["ban_clave"])]);
                usoCFDI = {};
                if len(arr_uso)>0:
                    usoCFDI = arr_uso[0];

                usoCFDI["clave_institucion_financiera"] = uso_cfdi["ban_clave"];
                usoCFDI["rfc_banco"] = uso_cfdi["ban_rfc"];
                usoCFDI["c_nombre"] = uso_cfdi["ban_nombre"];

                if len(arr_uso)>0:
                    obj_banco.update(usoCFDI);
                else:
                    obj_banco.create(usoCFDI);

        else:
            None;
