
from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo import tools
from odoo.tools.translate import _
import logging


class CfdiAlarm(models.Model):
    _name = 'cfdi.alarm'
    _description = 'Cfdi alarm'

    @api.depends('interval', 'duration')
    def _compute_duration_minutes(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_minutes = alarm.duration
            elif alarm.interval == "hours":
                alarm.duration_minutes = alarm.duration * 60
            elif alarm.interval == "days":
                alarm.duration_minutes = alarm.duration * 60 * 24
            else:
                alarm.duration_minutes = 0

    _interval_selection = {'minutes': 'Minute(s)', 'hours': 'Hour(s)', 'days': 'Day(s)'}


    name = fields.Char('Name', required=True)
    type = fields.Selection([('notification', 'Notification'), ('email', 'Email')], 'Type', required=True, default='email')
    duration = fields.Integer('Amount', required=True, default=1)
    interval = fields.Selection(list(_interval_selection.iteritems()), 'Unit', required=True, default='hours')
    duration_minutes = fields.Integer('Duration in minutes', compute='_compute_duration_minutes', store=True, help="Duration in minutes")


    def _update_cron(self):
        _logger = logging.getLogger(__name__)
        #_logger.info("Entra a update cron")
        try:
            cron = self.env['ir.model.data'].sudo().get_object('cfdi', 'ir_cron_scheduler_alarm')
        except ValueError:
            return False
        return cron.toggle(model=self._name, domain=[('type', '=', 'notification')])

    @api.model
    def create(self, values):
        _logger = logging.getLogger(__name__)
        #_logger.info("Entra a create")
        result = super(CfdiAlarm, self).create(values)
        self._update_cron()
        return result

    @api.multi
    def write(self, values):
        _logger = logging.getLogger(__name__)
        #_logger.info("Entra a write")
        result = super(CfdiAlarm, self).write(values)
        self._update_cron()
        return result



