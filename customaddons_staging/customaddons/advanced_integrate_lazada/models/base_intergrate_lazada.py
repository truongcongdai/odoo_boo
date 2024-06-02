from odoo import fields, models
import requests
import time
import hmac
import hashlib
import json
import urllib.parse
from odoo.http import request, _logger

class IntegrateLazada(models.Model):
    _name = 'base.integrate.lazada'

    def create_signature(self, api, parameters):
        ir_config = self.env['ir.config_parameter'].sudo()
        sort_dict = sorted(parameters)
        secret = ir_config.get_param('intergrate_lazada.app_secret','')
        parameters_str = "%s%s" % (api,str().join('%s%s' % (key, parameters[key]) for key in sort_dict))
        h = hmac.new(secret.encode(encoding="utf-8"), parameters_str.encode(encoding="utf-8"), digestmod=hashlib.sha256)
        return h.hexdigest().upper()

    def _post_data_lazada(self, api, parameters=None):
        headers = {
            'User-Agent': 'Odoo'
        }
        ir_config = self.env['ir.config_parameter'].sudo()
        params = {
            "app_key": ir_config.get_param('intergrate_lazada.app_key', ''),
            "sign_method": "sha256",
            "access_token": ir_config.get_param('intergrate_lazada.access_token', ''),
            "timestamp": int(round(time.time() * 1000))
        }
        if parameters:
            if len(parameters) == 1:
                key = list(parameters.keys())[0]
                params.update({key: str(parameters[key])})
            else:
                params.update(parameters)
        sign = self.create_signature(api, parameters=params)
        params.update({
            'sign': sign
        })
        url = ir_config.get_param('intergrate_lazada.url', '') + api
        res = requests.post(
            url,
            data={},
            params=params,
            headers=headers,
            verify=False
        )
        _logger.info('check /product/stock/sellable/update')
        _logger.info(res)
        _logger.info(params)
        _logger.info('end_check /product/stock/sellable/update')
        if res and res.status_code == 200:
            return res.json()
        return res

    def _get_data_lazada(self, api, parameters=None, files=None, headers=None):
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo'
            }
        if parameters is None:
            parameters = {}
        ir_config = self.env['ir.config_parameter'].sudo()

        timestamp = int(round(time.time() * 1000))
        params = {"app_key": ir_config.get_param('intergrate_lazada.app_key', ''), "sign_method": "sha256",
                  "access_token": ir_config.get_param('intergrate_lazada.access_token', ''), "timestamp": timestamp}
        params.update(parameters)
        sign = self.create_signature(api, parameters=params)
        params.update({"sign": sign})

        url = ir_config.get_param('intergrate_lazada.url', '') + api
        res = requests.get(
            url,
            data={},
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        _logger.info('check /product/stock/sellable/update')
        _logger.info(res)
        _logger.info(params)
        _logger.info('end_check /product/stock/sellable/update')
        if res:
            if res.status_code == 200:
                return res.json()
