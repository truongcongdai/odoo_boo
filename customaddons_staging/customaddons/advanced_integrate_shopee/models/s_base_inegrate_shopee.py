from odoo import fields, models
import hmac
import json
import time
import hashlib
import requests
from odoo.exceptions import ValidationError, _logger


class SBaseIntergrateShopee(models.Model):
    _name = "s.base.integrate.shopee"

    def _create_signature(self, api, timest, shop_id, app_key):
        app_secret = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_shopee.shopee_app_secret', '')
        access_token = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_shopee.access_token_shopee')
        tmp_base_string = "%s%s%s%s%s" % (app_key, api, timest, access_token, shop_id)
        base_string = tmp_base_string.encode()
        partner_key = app_secret.encode()
        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
        return sign

    def _get_data_shopee(self, api, payload=None, files=None, param=None, headers=None):
        if param is None:
            param = {}
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo'
            }
        ir_config = self.env['ir.config_parameter'].sudo()
        app_key = int(ir_config.get_param('advanced_integrate_shopee.shopee_app_key', ''))
        shop_id = int(ir_config.get_param('advanced_integrate_shopee.shopee_shop_id', ''))
        timest = int(time.time())
        sign = self._create_signature(api, timest, shop_id, app_key)
        data = payload or dict()
        data = data or dict()
        ir_config = self.env['ir.config_parameter'].sudo()
        params = {
            "partner_id": app_key,
            "shop_id": shop_id,
            "timestamp": timest,
            "access_token": self.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_shopee.access_token_shopee'),
            "sign": sign,
        }
        params.update(param)
        url = ir_config.get_param('advanced_integrate_shopee.shopee_url', '') + api
        res = requests.get(
            url,
            data=data,
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        return res

    def _post_data_shopee(self, api, data=None, files=None, param=None, headers=None):
        if param is None:
            param = {}
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo'
            }
        ir_config = self.env['ir.config_parameter'].sudo()
        app_key = int(ir_config.get_param('advanced_integrate_shopee.shopee_app_key', ''))
        shop_id = int(ir_config.get_param('advanced_integrate_shopee.shopee_shop_id', ''))
        timest = int(time.time())
        sign = self._create_signature(api, timest, shop_id, app_key)
        data = data or dict()
        params = {
            "partner_id": app_key,
            "shop_id": shop_id,
            "timestamp": timest,
            "access_token": self.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_shopee.access_token_shopee'),
            "sign": sign,
        }
        params.update(param)
        url = ir_config.get_param('advanced_integrate_shopee.shopee_url', '') + api
        res = requests.post(
            url,
            data=data,
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        _logger.info('start check' + str(url))
        _logger.info(data)
        _logger.info('end check cronjob_update_stock_skus_general_product_shopee')
        return res

    def _post_data_shipping_label_shopee(self, api, data=None, files=None, param=None, headers=None):
        if param is None:
            param = {}
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo'
            }
        ir_config = self.env['ir.config_parameter'].sudo()
        app_key = int(ir_config.get_param('advanced_integrate_shopee.shopee_app_key', ''))
        shop_id = int(ir_config.get_param('advanced_integrate_shopee.shopee_shop_id', ''))
        timest = int(time.time())
        sign = self._create_signature(api, timest, shop_id, app_key)
        data = data or dict()
        params = {
            "partner_id": app_key,
            "shop_id": shop_id,
            "timestamp": timest,
            "access_token": self.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_shopee.access_token_shopee'),
            "sign": sign,
        }
        params.update(param)
        url = ir_config.get_param('advanced_integrate_shopee.shopee_url', '') + api
        res = requests.post(
            url,
            data=data,
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        if res.status_code == 200:
            return res

    def get_shop_info_shopee(self):
        url_api = "/api/v2/shop/get_shop_info"
        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=url_api)
        if req is not None and req.get('error') == '':
            return req
