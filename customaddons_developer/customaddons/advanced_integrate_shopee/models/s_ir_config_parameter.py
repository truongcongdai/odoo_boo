import hashlib
import hmac
import json
from datetime import date
import time

import requests

from odoo import fields, models, api
from odoo.exceptions import ValidationError, _logger


class SIrConfigParameter(models.Model):
    _inherit = ['ir.config_parameter']

    def btn_refresh_token_shopee(self):
        timest = int(time.time())
        host = self.sudo().get_param('advanced_integrate_shopee.shopee_url', '')
        shop_id = int(self.sudo().get_param('advanced_integrate_shopee.shopee_shop_id', ''))
        refresh_token = self.sudo().get_param('advanced_integrate_shopee.refresh_token_shopee', '')
        partner_id = int(self.sudo().get_param('advanced_integrate_shopee.shopee_app_key', ''))
        tmp_partner_key = self.sudo().get_param('advanced_integrate_shopee.shopee_app_secret', '')
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
            self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.shopee_expire_in',
                                                             res.get('expire_in'))
        else:

            self.env['ir.logging'].sudo().create({
                'name': 'Refresh_token_Shope',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': res.get('error'),
                'func': 'btn_refresh_token_shopee',
                'line': '0',
            })
