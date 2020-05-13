odoo.define('sft-facturacion.pos_facturacion', function (require) {
"use strict";

var module = require('point_of_sale.models');
var chrome = require('point_of_sale.chrome');
var core = require('web.core');
var gui = require('point_of_sale.gui');
var rpc = require('web.rpc');
var screens = require('point_of_sale.screens');
var _t = core._t;

    console.log("--------------------------------------------------->pos_facturacion");
    //console.log(modelo.models);
    console.log("--------------------------------------------------->pos_facturacion2");
    module.PosModel.include({
	    initialize: function() {
            console.log("------------------initialize");
            var modelo = _super_order.initialize.apply(this,arguments);
            models = modelo.models;
            console.log(models);
            modelo_uso_cfdi = {
                model:  'cfdi.uso_cfdi',
                fields: [],
                domain: null,
                context: function(self){ return { active_test: false }; },
                loaded: function(self,units){
                    self.units = units;
                    _.each(units, function(unit){
                        self.units_by_id[unit.id] = unit;
                    });
                }
            };
            models.push(modelo_uso_cfdi);
            console.log(models);

        }
    });
});

