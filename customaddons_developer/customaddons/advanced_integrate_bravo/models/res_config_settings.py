from odoo import fields, models
import logging
from odoo.http import request
import requests
_logger = logging.getLogger(__name__)
from datetime import date
from odoo.exceptions import ValidationError
# from ..models.base_integrate_bravo import connect_bravo


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    bravo_url = fields.Char(
        string='Bravo API URL',
        config_parameter='bravo.url'
    )
    bravo_token = fields.Char(
        string='Bravo Token',
        config_parameter='bravo.token'
    )
    bravo_username = fields.Char(
        string='Bravo Username',
        config_parameter='bravo.username'
    )
    bravo_password = fields.Char(
        string='Bravo Password',
        config_parameter='bravo.password'
    )
    bravo_is_connected = fields.Boolean(
        string='Trạng thái kết nối Bravo',
        config_parameter='bravo.bravo_is_connected'
    )
    bravo_connected_date = fields.Datetime(
        string='Ngày kết nối Bravo',
        config_parameter='bravo.bravo_connected_date'
    )
    bravo_expires_days = fields.Integer(
        string='Thời gian hết hạn Token Bravo',
        config_parameter='bravo.bravo_expires_days'
    )
    bravo_push_limit = fields.Integer(
        string='Bravo push limit',
        config_parameter='bravo.push.limit'
    )

    def action_view_bravo_product_cron(self):
        cron_action = self.env.ref('base.ir_cron_act').read()[0]
        view_id = self.env.ref('base.ir_cron_view_form').id
        res_id = self.env.ref('advanced_integrate_bravo.ir_cron_sync_bravo_product').id
        cron_action['view_mode'] = 'form'
        cron_action['views'] = [[view_id, 'form']]
        cron_action['view_id'] = (view_id, 'ir.cron.view.form')
        cron_action['res_id'] = res_id
        return cron_action

    def action_connect_bravo(self):
        integrate_bravo = self.env['base.integrate.bravo'].sudo().connect_bravo()
        return integrate_bravo

    def action_disconnect_bravo(self):
        self.env['ir.config_parameter'].sudo().set_param('bravo.bravo_is_connected', False)
        self.env['ir.config_parameter'].sudo().set_param('bravo.password', None)
