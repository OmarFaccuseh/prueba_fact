odoo.define('account.sat_pendiente_cancelacion', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var core = require('web.core');
var Notification = require('web.notification').Notification;
var session = require('web.session');
var WebClient = require('web.WebClient');

var FieldMany2ManyTags = core.form_widget_registry.get('many2many_tags');
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

var CfdiNotification = Notification.extend({
    template: "CfdiCancelacion",

    init: function(parent, title, text, eid) {
        this._super(parent, title, text, true);
        this.eid = eid;

        this.events = _.extend(this.events || {}, {

            'click .link2recall': function() {
                this.destroy(true);
            },

            'click .link2showed': function() {
                this.destroy(true);
                this.rpc("/cfdi/notify_ack");
            },
        });
        //bus.start_polling();
    },
});

WebClient.include({
    display_cfdi_notif: function(notifications) {
        var self = this;
        var last_notif_timer = 0;
        console.log("CFDI: display_cfdi_notif");

        // Clear previously set timeouts and destroy currently displayed calendar notifications
        clearTimeout(this.get_next_cfdi_notif_timeout);
        _.each(this.cfdi_notif_timeouts, clearTimeout);
        _.each(this.cfdi_notif, function(notif) {
            if (!notif.isDestroyed()) {
                notif.destroy();
            }
        });
        this.cfdi_notif_timeouts = {};
        this.cfdi_notif = {};

        // For each notification, set a timeout to display it
        _.each(notifications, function(notif) {
            self.cfdi_notif_timeouts[notif.event_id] = setTimeout(function() {
                var notification = new CfdiNotification(self.notification_manager, notif.title, notif.message, notif.event_id);
                self.notification_manager.display(notification);
                self.cfdi_notif[notif.event_id] = notification;
            }, notif.timer * 1000);
            last_notif_timer = Math.max(last_notif_timer, notif.timer);
        });

        // Set a timeout to get the next notifications when the last one has been displayed
        if (last_notif_timer > 0) {
            this.get_next_cfdi_notif_timeout = setTimeout(this.get_next_cfdi_notif.bind(this), last_notif_timer * 1000);
        }
    },
    get_next_cfdi_notif: function() {
        this.rpc("/cfdi/notify", {}, {shadow: true})
            .done(this.display_cfdi_notif.bind(this))
            .fail(function(err, ev) {
                if(err.code === -32098) {
                    // Prevent the CrashManager to display an error
                    // in case of an xhr error not due to a server error
                    ev.preventDefault();
                }
            });
    },
    show_application: function() {
        // An event is triggered on the bus each time a calendar event with alarm
        // in which the current user is involved is created, edited or deleted
        this.cfdinotif_timeouts = {};
        this.cfdi_notif = {};
        console.log("CFDI: show_application");
        bus.on('notification', this, function (notifications) {
            _.each(notifications, (function (notification) {
                console.log(notification[0][1]);
                if (notification[0][1] === 'cfdi.alarm') {
                    console.log("CFD: display_cfdi_notif");
                    this.display_cfdi_notif(notification[1]);
                }
            }).bind(this));
        });
        return this._super.apply(this, arguments).then(this.get_next_cfdi_notif.bind(this));
    },
});


});
