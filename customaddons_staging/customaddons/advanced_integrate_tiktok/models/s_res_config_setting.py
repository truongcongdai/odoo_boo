from datetime import date

import requests

from odoo import fields, models, api
from odoo.exceptions import ValidationError, _logger
from ..tools.api_wrapper_tiktok import validate_integrate_token


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    tiktok_auth_key = fields.Char(string='Authorization Key Tiktok', config_parameter='tiktok.auth.key')
    tiktok_api_url = fields.Char(string='API URL Tiktok', config_parameter='tiktok.api_url')
    tiktok_api_url_oauth = fields.Char(string='API URL OAUTH Tiktok', config_parameter='tiktok.api_url_oauth')
    tiktok_app_key = fields.Char(string="App Key Tiktok", config_parameter='tiktok.app.key')
    tiktok_app_secret = fields.Char(string="App Secret Tiktok", config_parameter='tiktok.app.secret')
    tiktok_service_id = fields.Char(string="Service Id Tiktok", config_parameter='tiktok.service.id')
    callback_url = fields.Char(string="Callback url Tiktok", config_parameter='tiktok.callback_url')
    access_token_tiktok = fields.Char(string="Access Token Tiktok", config_parameter='tiktok.access_token')
    refresh_token_tiktok = fields.Char(string="Refresh Token Tiktok", config_parameter='tiktok.refresh_token')
    access_token_expire_in = fields.Char(string="Expire Token Tiktok", config_parameter='tiktok.access_token_expire_in')
    tiktok_connected_date = fields.Char(string="Service Id Tiktok", config_parameter='tiktok.connect_date')
    is_connect_tiktok = fields.Boolean(config_parameter='tiktok.is_connect')
    tiktok_mode = fields.Selection(
        [('sandbox', 'sandbox'), ('service_none_us', 'service none us'),
         ('service_us', 'service us')], string="Tiktok Mode", config_parameter='tiktok.tiktok_mode')
    tiktok_refresh_url = fields.Char(string='Url refesh Tiktok', config_parameter='tiktok.url_refresh')
    s_tiktok_sync_stock = fields.Boolean(string="Đồng bộ tồn kho tự động", config_parameter='tiktok.s_tiktok_sync_stock')
    s_tiktok_sync_stock_end_of_day = fields.Boolean(string="Đồng bộ cuối ngày", config_parameter='tiktok.s_tiktok_sync_stock_end_of_day')
    s_tiktok_set_time_start = fields.Datetime(string="Thời gian bắt đầu", config_parameter='tiktok.s_tiktok_set_time_start')

    @api.onchange("tiktok_mode")
    def _onchange_tiktok_mode(self):
        if self.tiktok_mode == "sandbox":
            self.env['ir.config_parameter'].sudo().set_param('tiktok.api_url_oauth',
                                                             'https://auth-sandbox.tiktok-shops.com')
            self.env['ir.config_parameter'].sudo().set_param('tiktok.api_url',
                                                             'https://open-api-sandbox.tiktokglobalshop.com')
            self.env['ir.config_parameter'].sudo().set_param('tiktok.url_refresh',
                                                             'https://auth-sandbox.tiktok-shops.com')
        elif self.tiktok_mode == "service_none_us":
            self.env['ir.config_parameter'].sudo().set_param('tiktok.api_url_oauth', 'https://services.tiktokshop.com')
            self.env['ir.config_parameter'].sudo().set_param('tiktok.api_url',
                                                             'https://open-api.tiktokglobalshop.com')
            self.env['ir.config_parameter'].sudo().set_param('tiktok.url_refresh', 'https://auth.tiktok-shops.com')
        elif self.tiktok_mode == "service_us":
            self.env['ir.config_parameter'].sudo().set_param('tiktok.api_url_oauth',
                                                             'https://services.us.tiktokshop.com')
            self.env['ir.config_parameter'].sudo().set_param('tiktok.api_url',
                                                             'https://open-api.tiktokglobalshop.com')

    def btn_connect_tiktok(self):
        if self.tiktok_app_key:
            url = ""
            if self.tiktok_mode == "sandbox":
                url = "%s/open/authorize?app_key=%s&state=123" % (
                    self.env['ir.config_parameter'].sudo().get_param('tiktok.api_url_oauth'), self.tiktok_app_key)
            elif self.tiktok_mode in ["service_none_us", "service_us"]:
                url = "%s/open/authorize?service_id=%s&state=123" % (
                    self.env['ir.config_parameter'].sudo().get_param('tiktok.api_url_oauth'), self.tiktok_service_id)
            if len(url) > 0:
                return {
                    'name': 'AuthorizationTiktok',
                    'type': 'ir.actions.act_url',
                    'url': url,  # Replace this with tracking link
                    'target': 'new',  # you can change target to current, self, new.. etc
                }
            else:
                raise ValidationError("Xin vui lòng chọn tiktok mode!")
        else:
            raise ValidationError("Invalid Client ID")

    def refresh_token(self):
        app_key = self.env['ir.config_parameter'].sudo().get_param('tiktok.app.key', '')
        app_secret = self.env['ir.config_parameter'].sudo().get_param('tiktok.app.secret', '')
        refresh_token = self.env['ir.config_parameter'].sudo().get_param('tiktok.refresh_token', '')
        url = self.env['ir.config_parameter'].sudo().get_param('tiktok.url_refresh', '') + "/api/v2/token/refresh"
        params = dict(
            app_key=app_key,
            app_secret=app_secret,
            refresh_token=refresh_token,
            grant_type='refresh_token'
        )
        res = requests.get(
            url=url,
            params=params
        )
        if res.status_code == 200:
            response = res.json()
            if response.get('code') == 0 and response.get('message') == 'success':
                access_token_tiktok = response['data'].get('access_token', '')
                self.env['ir.config_parameter'].sudo().set_param('tiktok.access_token', access_token_tiktok)
                self.env['ir.config_parameter'].sudo().set_param('tiktok.refresh_token',
                                                                 response['data'].get('refresh_token', ''))
                self.env['ir.config_parameter'].sudo().set_param('tiktok.access_token_expire_in',
                                                                 response['data'].get('access_token_expire_in', ''))
                self.env['ir.config_parameter'].sudo().set_param('tiktok.connect_date', date.today())
                self.env['ir.config_parameter'].sudo().set_param('tiktok.is_connect', True)

    def btn_disconnect_tiktok(self):
        self.env['ir.config_parameter'].sudo().set_param('tiktok.is_connect', False)
        self.env['ir.config_parameter'].sudo().set_param('tiktok.access_token', '')
        self.env['ir.config_parameter'].sudo().set_param('tiktok.refresh_token', '')
        self.env['ir.config_parameter'].sudo().set_param('tiktok.access_token_expire_in', '')
        self.env['ir.config_parameter'].sudo().set_param('tiktok.auth.key', '')
