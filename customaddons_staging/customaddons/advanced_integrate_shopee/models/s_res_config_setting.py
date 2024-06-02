import hashlib
import hmac
import json
from datetime import date
import time

import requests

from odoo import fields, models, api
from odoo.exceptions import ValidationError, _logger


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    shopee_shop_id = fields.Char(string='Shop Id Shopee', config_parameter='advanced_integrate_shopee.shopee_shop_id')
    shopee_app_key = fields.Char(string="App Key Shopee", config_parameter='advanced_integrate_shopee.shopee_app_key')
    shopee_app_secret = fields.Char(string="App Secret Shopee", config_parameter='advanced_integrate_shopee.shopee_app_secret')
    shopee_expire_in = fields.Integer(string="App Secret Shopee", config_parameter='advanced_integrate_shopee.shopee_expire_in')
    shopee_url = fields.Char(string="Callback url Shopee",
                             config_parameter='advanced_integrate_shopee.shopee_url')
    access_token_shopee = fields.Char(string="Access Token Shopee",
                                      config_parameter='advanced_integrate_shopee.access_token_shopee')
    refresh_token_shopee = fields.Char(string="Refresh Token Shopee",
                                       config_parameter='advanced_integrate_shopee.refresh_token_shopee')
    shopee_connected_date = fields.Char(string="Service Id Shopee",
                                        config_parameter='advanced_integrate_shopee.shopee_connected_date')
    is_connect_shopee = fields.Boolean(config_parameter='advanced_integrate_shopee.is_connect_shopee')
    is_error_token_shopee = fields.Char(config_parameter='advanced_integrate_shopee.is_error_token_shopee', default='False')
    s_shopee_sync_stock = fields.Boolean(string="Đồng bộ tồn kho tự động",
                                         config_parameter='advanced_integrate_shopee.s_shopee_sync_stock')
    s_shopee_set_time_start = fields.Datetime(string="Shopee Thời gian bắt đầu đồng bộ tồn kho tự động",
                                              config_parameter='advanced_integrate_shopee.s_shopee_set_time_start')
    s_shopee_sync_stock_end_of_day = fields.Boolean(string="Shopee Đồng bộ tồn kho cuối ngày",
                                                    config_parameter='advanced_integrate_shopee.s_shopee_sync_stock_end_of_day')

    def btn_connect_shopee(self):
        if self.shopee_app_key and self.shopee_app_secret:
            timest = int(time.time())
            host = self.shopee_url
            path = "/api/v2/shop/auth_partner"
            redirect_url = "{base_url}/shopee/callback".format(
                base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
            partner_id = int(self.shopee_app_key)
            tmp = self.shopee_app_secret
            partner_key = tmp.encode()
            tmp_base_string = "%s%s%s" % (partner_id, path, timest)
            base_string = tmp_base_string.encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            url = host + path + "?partner_id=%s&timestamp=%s&redirect=%s&sign=%s" % (
                partner_id, timest, redirect_url, sign)
            return {
                'name': 'Authorization',
                'type': 'ir.actions.act_url',
                'url': url,  # Replace this with tracking link
                'target': 'new',  # you can change target to current, self, new.. etc
            }
        else:
            raise ValidationError("Invalid Client ID")

    def btn_disconnect_shopee(self):
        self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.is_connect_shopee', False)
        self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.access_token_shopee', '')
        self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.refresh_token_shopee', '')
        self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.shopee_shop_id', '')
        self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.is_error_token_shopee', 'False')
        self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.shopee_expire_in', False)

    def button_refresh_token_shopee(self):
        timest = int(time.time())
        host = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_shopee.shopee_url', '')
        shop_id = int(self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_shopee.shopee_shop_id', ''))
        refresh_token = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_shopee.refresh_token_shopee', '')
        partner_id = int(self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_shopee.shopee_app_key', ''))
        tmp_partner_key = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_shopee.shopee_app_secret', '')
        path = "/api/v2/auth/access_token/get"
        body = {"shop_id": shop_id, "refresh_token": refresh_token, "partner_id": partner_id}
        tmp_base_string = "%s%s%s" % (partner_id, path, timest)
        base_string = tmp_base_string.encode()
        partner_key = tmp_partner_key.encode()
        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
        url = host + path + "?partner_id=%s&timestamp=%s&sign=%s" % (partner_id, timest, sign)
        headers = {"Content-Type": "application/json", "User-Agent": "Odoo"}
        res = requests.post(url, json=body, headers=headers).json()
        if res is not None and not res.get('error'):
            self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.access_token_shopee',
                                                             res.get('access_token'))
            self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.refresh_token_shopee',
                                                             res.get('refresh_token'))
            self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.is_error_token_shopee', 'False')
        else:
            raise ValidationError(res.get('message'))