# -*- coding: utf-8 -*-
import json
import requests
import hashlib
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import models, fields, api
import logging


class Configuracion(models.Model):
    _name = 'cfdi.configuracion'
    _description = u"Configuracion del usuario y contraseña para el timbrado de la factura"
    _rec_name = "usuario"

    @api.one
    def _encriptada(self):

        string=str(self.contrasena)
        #crea el algoritmo para encriptar la informacion
        algorithim=hashlib.md5()
        #encripta la informacion
        algorithim.update(string.encode('utf-8'))
        #La decodifica en formato hexadecimal
        encrypted=algorithim.hexdigest()
        self.encriptada = encrypted;

    url = fields.Char(string='URL', required=True, )
    usuario = fields.Char(string='Usuario', required=True, )
    contrasena = fields.Char(string='Contraseña', required=True)
    encriptada = fields.Char(string='Contraseña encriptada', compute=_encriptada)
    state = fields.Selection([
        ('validar', 'No Confirmado'),
        ('validado', 'Validado'),
    ], string='Status', index=True, readonly=True, default='validar',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.", color="green")

    @api.multi
    def validar_usuario(self):

        service = str(self.url) + "webresources/UsuarioWS/ValidarUsuarioOdoo"
        string = str(self.contrasena)
        # crea el algoritmo para encriptar la informacion
        algorithim = hashlib.md5()
        # encripta la informacion
        algorithim.update(string.encode("utf-8"))
        # La decodifica en formato hexadecimal
        encrypted = algorithim.hexdigest()

        data = {
            "user_odoo": self.usuario, "odoo_contrasena": encrypted, "odoo_pfl_id": "4"
        }

        headers = {
            'content-type': "application/json"
        }
        print(data)
        _logger = logging.getLogger(__name__)
        _logger.info(data)
        response = requests.request("POST", service, data=json.dumps(data), headers=headers)
        json_data = json.loads(response.text)
        # Valida que la factura haya sido timbrada Correctamente
        if json_data['result']['success'] == 'true':
            self.state = 'validado'
        # tkinter.messagebox.showinfo('Resultado','Usuario Valido')
        # raise ValidationError("Texto Encriptado %s Encriptacion %s" %(string,encrypted))
        else:
            raise ValidationError(json_data['result']['message'])

    @api.multi
    def volver_a_validar_usuario(self):
        self.state = 'validar'

    @api.onchange('usuario')
    def _onchange_sin_validar_usuario(self):
        self.state = 'validar'

    @api.onchange('url')
    def _onchange_url(self):
        if self.url!= None and self.url != False:
            if self.url[len(self.url) - 1] != '/':
                self.url = self.url + "/";

    #ObtenerUsoCfdi
    #ObtenerTasaoCuota
    #ObtenerMetodoPago
    #ObtenerMoneda
    #ObtenerRegimenFiscal
    #ObtenerProductoServicio
    #ObtenerFormaPago
    @api.model
    def sincronizaCatalogos(self):
        obj_uso_cfdi = self.env['cfdi.uso_cfdi'];
        obj_uso_cfdi.sincroniza();

        obj_tasa_cuota = self.env['cfdi.tasa_cuota'];
        obj_tasa_cuota.sincroniza();

        obj_metodo_pago = self.env['cfdi.metodo_pago']
        obj_metodo_pago.sincroniza();

        obj_regimen = self.env['account.fiscal.position']
        obj_regimen.sincroniza();

        obj_forma_pago = self.env['cfdi.forma_pago']
        obj_forma_pago.sincroniza();

        obj_tipo_relacion = self.env['cfdi.tipo_relacion']
        obj_tipo_relacion.sincroniza();

        obj_impuesto = self.env['cfdi.impuestos']
        obj_impuesto.sincroniza();

        obj_tipo_factor = self.env['cfdi.tipo_factor']
        obj_tipo_factor.sincroniza();

        obj_banco = self.env['cfdi.bancos']
        obj_banco.sincroniza();

        obj_prod = self.env['cfdi.clave_prod_serv']
        obj_prod.sincroniza();

        obj_unidad = self.env['cfdi.clave_unidad']
        obj_unidad.sincroniza();




