# -*- coding: utf-8 -*-

import datetime
import logging
import hashlib
import json
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class SATPendienteCancelar(models.Model):
    _name = 'account.sat_pendiente_cancelacion'
    _logger = logging.getLogger(__name__)

    UUID = fields.Char("Clave")
    estado = fields.Char("Error", default="Pendiente")
    fecha_respuesta = fields.Date("Fecha respuesta")
    #usuario_respuesta = fields.Char("Usuario que responde")
    usuario_respuesta = fields.Many2one('res.users', "Usuario que responde")
    compania_rfc = fields.Char("Compañía")
    servicio_mensaje = fields.Char("Mensaje de servicio")


    configuracion = None
    usuario = None;
    password = None;


    def test_act(self,cr,uid,ids,context={}):
        print("test_act")
        return True

    @api.model
    def consulta_automatica_sft(self):
        self.inicializaConfiguracion();
        self.buscaCanceladasPendientes();
        self.buscaPorcancelar();

    def inicializaConfiguracion(self):
        self._logger.info("inicializaConfiguracion")

        self.configuracion = self.env['cfdi.configuracion'].search([('url', '!=', '')])
        self.usuario = self.configuracion.usuario
        contrasena=self.configuracion.contrasena

        string=str(contrasena.encode("utf-8"))
        #crea el algoritmo para encriptar la informacion
        algorithim=hashlib.md5()
        #encripta la informacion
        algorithim.update(string)
        #La decodifica en formato hexadecimal
        self.password=algorithim.hexdigest()

    #Busca las facturas que cancelaste y está pendiente que el cliente autorice o rechace
    def buscaCanceladasPendientes(self):
        self._logger.info("buscaCanceladasPendientes")

        facturas = self.env['account.invoice'].search([('fac_estatus_cancelacion', '=', 'En proceso')])
        arr_facturas = [];
        for factura in facturas:
            string=str(str(factura.fac_id).encode("utf-8"))
            algorithim=hashlib.md5()
            algorithim.update(string)
            encrypted=algorithim.hexdigest()
            factura_mds ={"factura":encrypted};
            self._logger.info(factura_mds)
            arr_facturas.append(factura_mds);

        url = str(self.configuracion.url)+"webresources/FacturacionWS/ObtenerSatEstatusFacturas"
        self._logger.info(url)
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }
        data = {
            "usuario" : self.usuario,
            "contrasena" : self.password,
            "facturas" : arr_facturas,
            "emisor":self.env.user.company_id.company_registry
        };

        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(response.text)
        json_data = json.loads(response.text)

        for acuse in json_data["acuse"]:
            facturas = self.env['account.invoice'].search([('uuid', '=', acuse["uuid"] )])
            if acuse["estatus"] == 'Cancelado':
                for factura in facturas:
                    datos = {};
                    datos["state"] = "timbrada";
                    datos["fac_timbrada"] = 'Timbre Cancelado'
                    #datos["fac_estatus_cancelacion"] = acuse["EstatusCancelacion"]
                    if acuse["EstatusCancelacion"] == "Plazo vencido":
                        datos["fac_estatus_cancelacion"] = acuse["EstatusCancelacion"]
                    else:
                        datos["fac_estatus_cancelacion"] = "Cancelación Aceptada"

                    factura.cancelaFacturaNuevoProceso();
                    datos["state"] = 'cancel'
                    factura.write(datos);

            # if acuse["estatus"] == 'Rechazado':
            #     for factura in facturas:
            #         datos = {};
            #         datos["state"] = "timbrada";
            #         datos["fac_timbrada"] = 'Timbrada'
            #         datos["fac_estatus_cancelacion"] = acuse["EstatusCancelacion"]
            #         factura.write(datos);

            if acuse["estatus"] == 'Vigente' and "EstatusCancelacion" not in acuse:#Si está vigente, es por que rechazó la cancelación
                for factura in facturas:
                    datos = {};
                    datos["state"] = "timbrada";
                    datos["fac_timbrada"] = 'Timbrada'
                    #datos["fac_estatus_cancelacion"] = acuse["EstatusCancelacion"]
                    datos["fac_estatus_cancelacion"] = "Cancelación Rechazada"
                    factura.write(datos);



    def buscaPorcancelar(self):
        self._logger.info("buscaPorcancelar")
        url = str(self.configuracion.url)+"webresources/FacturacionWS/ObtenerCancelacionesPendientes"
        self._logger.info(url)
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }
        data = {
            "usuario" : self.usuario,
            "contrasena" : self.password
        };
        companias = self.env['res.company'].search([('company_registry', '!=', '')])
        for compania in companias:
            data["receptor"] = compania.company_registry
            self._logger.info(data)
            response = requests.request("POST", url, data=json.dumps(data), headers=headers)
            json_data = json.loads(response.text)
            self._logger.info(json_data)

            uuids = json_data["result"]["uuids"];
            self._logger.info(uuids)

            for uuid in uuids:
                #Busca si el uuid no ha sido importado
                pendientes_cncelcion = self.env['account.sat_pendiente_cancelacion'].search([('UUID', '=', uuid ),('compania_rfc', '=', compania.company_registry )])
                if len(pendientes_cncelcion) == 0:
                    data_insert ={
                        "UUID":uuid,
                        "compania_rfc": compania.company_registry
                    }
                    self.env['account.sat_pendiente_cancelacion'].create(data_insert)
                    #self.env['account.sat_pendiente_cancelacion'].sudo().write(data_insert)





    def aceptar(self):
        self._logger.info("aceptar")
        self.proceza_acepta_rechaza("aceptaciones");

    def rechazar(self):
        self._logger.info("rechazar")
        self.proceza_acepta_rechaza("rechazos");

    def proceza_acepta_rechaza(self, proceso):
        self._logger.info("proceza_acepta_rechaza")
        self.inicializaConfiguracion();


        arr_seleccion = self.env['account.sat_pendiente_cancelacion'].browse(self._context.get('active_ids'))

        if len(arr_seleccion) == 0:
            raise ValidationError("No se han seleccionado facturas ")

        self._logger.info(self.env.user)
        arr_uuids = [];
        for seleccion in arr_seleccion:
            if self.env.user.company_id.company_registry != seleccion["compania_rfc"]:
                raise ValidationError("Las facturas seleccionaas tienen un RFC diferente a {0} ".format(self.env.user.comrpany_id.company_registry))
            uuid = {"uuid":seleccion["UUID"]};

            arr_uuids.append(uuid)



        url = str(self.configuracion.url)+"webresources/FacturacionWS/AceptarRechazarCancelacion"
        self._logger.info(url)
        headers = {
           'content-type': "application/json;charset=iso-8859-1", 'Authorization':"Basic YWRtaW46YWRtaW4="
        }
        data = {
            "usuario" : self.usuario,
            "contrasena" : self.password,
            "receptor": self.env.user.company_id.company_registry,
            "facturas":{
                proceso : arr_uuids
            }
        };

        estado_final = "";
        respuesta = "";
        if proceso == 'rechazos':
            estado_final = 'Rechazada'
            respuesta = 'respuestaRechazo';

        if proceso == 'aceptaciones':
            estado_final = 'Aceptada'
            respuesta = 'respuestaAceptacion';


        self._logger.info(data)
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        self._logger.info(url)
        json_data = json.loads(response.text)
        self._logger.info(response.text)
        fecha  = fields.Datetime.to_string(datetime.datetime.now())
        compania = self.env.user.company_id


        if json_data["result"]["success"] == 'true':
            for respuesta in json_data["result"]["acepta_rechaza"][respuesta]:
                #Busca la factura
                print(respuesta["uuid"])
                print(compania.company_registry)
                pendientes_cncelcion = self.env['account.sat_pendiente_cancelacion'].search([('UUID', '=', respuesta["uuid"] ),('compania_rfc', '=', compania.company_registry )])
                print(pendientes_cncelcion)
                if pendientes_cncelcion == None or pendientes_cncelcion == False or pendientes_cncelcion.id == None:
                    raise ValidationError("Error al obtener factura de UUID: "+respuesta["uuid"])

                data = {};
                if "error" in respuesta:
                    data["servicio_mensaje"] = respuesta["error"]
                else:
                    data["estado"] = estado_final;
                    data["fecha_respuesta"] = fecha;
                    data["usuario_respuesta"] = self.env.user.id ;
                print(data)
                pendientes_cncelcion.write(data)
        else:
            raise ValidationError("Error al procesar la solicitud")
