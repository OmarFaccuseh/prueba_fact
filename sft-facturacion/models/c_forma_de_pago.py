# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class FormaPago(models.Model):
    _name = 'cfdi.forma_pago'
    _description = u"Catálogo de formas de pago."
    _rec_name = "descripcion"

    _logger = logging.getLogger(__name__)

    c_forma_pago = fields.Char(string='c_FormaPago')
    descripcion = fields.Char(string='Descripción')
    bancarizado = fields.Char(string='Bancarizado')
    num_op = fields.Char(string='Número de operación')
    rfc_emisor = fields.Char(string='RFC del Emisor de la cuenta ordenante')
    cuenta_ordenante = fields.Char(string='Cuenta Ordenante')	
    patron_cta_ordenante = fields.Char(string='Patrón para cuenta ordenante')	
    rfc_emisor_cta_benef = fields.Char(string='RFC del Emisor/Cuenta de Beneficiario')	
    cta_benenf = fields.Char(string='Cuenta del Benenficiario')
    patron_cta_benef = fields.Char(string='Patrón para la cuenta Beneficiaria')	
    tipo_cad_pago = fields.Char(string='Tipo Cadena Pago')	
    nom_banco_emisor_cta_ord_ext = fields.Char(string='Nombre del Banco emisor de la cuenta ordenante en caso de extranjero')	
    fecha_inicio_de_vigencia = fields.Date(string='Fecha inicio de vigencia')	
    fecha_fin_de_vigencia = fields.Date(string='Fecha fin de vigencia')


    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerFormaPago"
        data = {};
        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_forma_pago = self.env['cfdi.forma_pago']
        if json_data["result"]["success"] == True:
            arr_forma_pago = json_data["result"]["formapago"];
            for ws_forma_pago in arr_forma_pago:
                None;
                arr_uso = obj_forma_pago.search([("c_forma_pago","=",ws_forma_pago["fop_clave"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];

                metodo["c_forma_pago"] = ws_forma_pago["fop_clave"];
                metodo["descripcion"] = ws_forma_pago["fop_descripcion"];
                metodo["bancarizado"] = ws_forma_pago["fop_bancarizado"];
                if "fop_numero_operacion" in ws_forma_pago:
                    metodo["num_op"] = ws_forma_pago["fop_numero_operacion"];
                if "fop_rfc_emisor_cuenta_ordenante" in ws_forma_pago:
                    metodo["rfc_emisor"] = ws_forma_pago["fop_rfc_emisor_cuenta_ordenante"];
                if "fop_cuenta_ordenante" in ws_forma_pago:
                    metodo["cuenta_ordenante"] = ws_forma_pago["fop_cuenta_ordenante"];

                if "fop_patron_cuenta_ordenante" in ws_forma_pago:
                    metodo["patron_cta_ordenante"] = ws_forma_pago["fop_patron_cuenta_ordenante"];

                if "fop_rfc_emisor_cuenta_beneficiario" in ws_forma_pago:
                    metodo["rfc_emisor_cta_benef"] = ws_forma_pago["fop_rfc_emisor_cuenta_beneficiario"];

                if "fop_cuenta_beneficiario" in ws_forma_pago:
                    metodo["cta_benenf"] = ws_forma_pago["fop_cuenta_beneficiario"];

                if "fop_patron_cuenta_beneficiaria" in ws_forma_pago:
                    metodo["patron_cta_benef"] = ws_forma_pago["fop_patron_cuenta_beneficiaria"];

                if "fop_tipo_cadena_pago" in ws_forma_pago:
                    metodo["tipo_cad_pago"] = ws_forma_pago["fop_tipo_cadena_pago"];

                if "fop_nombre_banco_emisor" in ws_forma_pago:
                    metodo["nom_banco_emisor_cta_ord_ext"] = ws_forma_pago["fop_nombre_banco_emisor"];
                if "fecha_inicio_de_vigencia" in ws_forma_pago:
                    metodo["fecha_inicio_de_vigencia"] = ws_forma_pago["fop_fecha_inicio_vigencia"];
                #metodo["fecha_fin_de_vigencia"] = ws_forma_pago["fop_clave"];

                if len(arr_uso)>0:
                    obj_forma_pago.update(metodo);
                else:
                    obj_forma_pago.create(metodo);

        else:
            None;
