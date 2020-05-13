# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import requests
import json

class ClaveProdServicios(models.Model):
    _name = 'cfdi.clave_prod_serv'
    _description=u"Catálogo de productos / servicios."
    _rec_name = 'descripcion'

    _logger = logging.getLogger(__name__)

    c_claveprodserv = fields.Text(string='c_CaveProdServ')
    descripcion = fields.Char(string='Descripcion')
    fechainiciovigencia = fields.Date(string='Inicio de Vigencia')
    fechafinvigencia = fields.Date(string='Fin de la Vigencia')	
    incluir_iva_trasladado = fields.Char(string='Incluir IVA Traslado')	
    incluir_ieps_trasladado = fields.Char(string='Incluir IEPS Trasladado')
    complemento_que_debe_incluir = fields.Char(string='Complemento que debe incluir')
    palabras_similares = fields.Char(string='Palabras Similares')


    def sincroniza(self):
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }

        url_parte = self.env['cfdi.configuracion'].search([('url', '!=', '')])[0].url;
        url = url_parte+"webresources/CatalogosSatWS/ObtenerProductoServicio"
        data = {};
        #self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        #self._logger.info(response.text)
        json_data = json.loads(response.text)

        obj_prod = self.env['cfdi.clave_prod_serv']
        if json_data["resultado"]["success"] == True:
            arr_productos = json_data["resultado"]["producto_servicios"];
            for ws_producto in arr_productos:
                None;
                arr_uso = obj_prod.search([("c_claveprodserv","=",ws_producto["prs_clave"])]);
                metodo = {};
                if len(arr_uso)>0:
                    metodo = arr_uso[0];

                metodo["c_claveprodserv"] = ws_producto["prs_clave"];
                metodo["descripcion"] = ws_producto["prs_descripcion"];
                metodo["fechainiciovigencia"] = ws_producto["prs_fecha_vigencia"];
                metodo["fechafinvigencia"] = ws_producto["prs_fecha_fin"];
                metodo["incluir_iva_trasladado"] = ws_producto["prs_iva_trasladado"];
                metodo["incluir_ieps_trasladado"] = ws_producto["prs_ieps_trasladado"];
                metodo["complemento_que_debe_incluir"] = ws_producto["prs_complemento"];
                metodo["palabras_similares"] = ws_producto["prs_palabras_similares"];



                if len(arr_uso)>0:
                    obj_prod.update(metodo);
                else:
                    obj_prod.create(metodo);

        else:
            None;

    
