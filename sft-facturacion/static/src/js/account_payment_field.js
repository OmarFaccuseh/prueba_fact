odoo.define('account.payment', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');


var QWeb = core.qweb;


var ShowPaymentLineWidget = AbstractField.extend({
    events: _.extend({
        'click .outstanding_credit_assign': '_onOutstandingCreditAssign',
    }, AbstractField.prototype.events),
    supportedFieldTypes: ['char'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {boolean}
     */
    isSet: function() {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _render: function() {
        var self = this;
        var info = JSON.parse(this.value);
        if (!info) {
            this.$el.html('');
            return;
        }
        _.each(info.content, function (k, v){
            k.index = v;
            k.amount = field_utils.format.float(k.amount, {digits: k.digits});
            if (k.date){
                k.date = field_utils.format.date(field_utils.parse.date(k.date, {}, {isUTC: true}));
            }
        });
        this.$el.html(QWeb.render('ShowPaymentInfo', {
            lines: info.content,
            outstanding: info.outstanding,
            title: info.title
        }));
        _.each(this.$('.js_payment_info'), function (k, v){
            var content = info.content[v];
            var options = {
                content: function () {
                    var $content = $(QWeb.render('PaymentPopOverSft', {
                        name: content.name,
                        journal_name: content.journal_name,
                        date: content.date,
                        amount: content.amount,
                        currency: content.currency,
                        position: content.position,
                        payment_id: content.payment_id,
                        move_id: content.move_id,
                        ref: content.ref,
                        payment_pago_id: content.payment_pago_id,
                        account_payment_id: content.account_payment_id,
                        invoice_id: content.invoice_id,
                    }));
                    $content.filter('.js_unreconcile_payment').on('click', self._onRemoveMoveReconcile.bind(self));
                    $content.filter('.js_open_payment').on('click', self._onOpenPayment.bind(self));
                    return $content;
                },
                html: true,
                placement: 'left',
                title: 'Payment Information',
                trigger: 'focus',
                delay: { "show": 0, "hide": 100 },
            };
            $(k).popover(options);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onOpenPayment: function (event) {
        var invoiceId = parseInt($(event.target).attr('invoice-id'));
        var paymentId = parseInt($(event.target).attr('payment-id'));
        var moveId = parseInt($(event.target).attr('move-id'));
        var payment_pago_id = parseInt($(event.target).attr('payment-pago-id'));
        console.log("pago: "+payment_pago_id)

        var res_model;
        var id;
        var el_this = this;
        if (payment_pago_id!== undefined && !isNaN(payment_pago_id) ){
            //ir_model_data = self.env['ir.model.data']
            var view_id;
            this._rpc({
                model: 'account.payment',
                method: 'obtiene_forma_pago',
                //The event can be called by a view that can have another context than the default one.
                args: [[payment_pago_id], event.context || self.context],
            }).then(function (viewId) {
                console.log("view_id "+viewId);
                view_id = viewId;
                el_this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'account.payment',
                    res_id: payment_pago_id,
                    view_type: 'form',
                    view_id :view_id,
                    views: [[false, 'form']],
                    target: 'current'
                });

            });

            console.log("view_id2 "+view_id);




            /*var model_obj = new instance.web.Model('ir.model.data');
            view_id = model_obj.get_object_reference('sft-facturacion','account_payment_sat_invoice_view')[1]
            model_obj.call('get_object_reference',['sft-facturacion','account_payment_sat_invoice_view']).then( function(result){
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'account.payment',
                    res_id: payment_pago_id,
                    view_type: 'form',
                    view_id :view_id,
                    views: [[false, 'form']],
                    target: 'current'
                });

            });*/

            /*this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'account.payment',
                res_id: payment_pago_id,
                view_type: 'form',
                //view_id :view_id,
                views: [[false, 'form']],
                target: 'current'
            });*/
        }else{
            if (invoiceId !== undefined && !isNaN(invoiceId)){
                res_model = "account.invoice";
                id = invoiceId;
            } else if (paymentId !== undefined && !isNaN(paymentId)){
                res_model = "account.payment";
                id = paymentId;
            } else if (moveId !== undefined && !isNaN(moveId)){
                res_model = "account.move";
                id = moveId;
            }
            //Open form view of account.move with id = move_id
            if (res_model && id) {
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: res_model,
                    res_id: id,
                    views: [[false, 'form']],
                    target: 'current'
                });
            }
        }




    },
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onOutstandingCreditAssign: function (event) {
        var self = this;
        var id = $(event.target).data('id') || false;
        this._rpc({
                model: 'account.invoice',
                method: 'assign_outstanding_credit',
                args: [JSON.parse(this.value).invoice_id, id],
            }).then(function () {
                self.trigger_up('reload');
            });
    },
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onRemoveMoveReconcile: function (event) {
        var self = this;
        var paymentId = parseInt($(event.target).attr('payment-id'));
        if (paymentId !== undefined && !isNaN(paymentId)){
            this._rpc({
                model: 'account.move.line',
                method: 'remove_move_reconcile',
                args: [paymentId, {'invoice_id': this.res_id}]
            }).then(function () {
                self.trigger_up('reload');
            });
        }
    },
});

field_registry.add('payment', ShowPaymentLineWidget);

});
