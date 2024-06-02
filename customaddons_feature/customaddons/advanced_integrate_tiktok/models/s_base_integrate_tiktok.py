from odoo import models, fields
import requests
import calendar
import time, hmac, hashlib
import urllib3
import pytz
from datetime import datetime, timedelta, date
from odoo.exceptions import ValidationError, _logger
urllib3.disable_warnings()


class BaseIntegrateTiktok(models.Model):
    _name = 'base.integrate.tiktok'
    token = fields.Char(string="Token Tiktok")

    # def get_token_tiktok(self):
    #     ir_config = self.env['ir.config_parameter'].sudo()
    #     app_key = ir_config.get_param('tiktok.app.key', '')
    #     auth_code = ir_config.get_param('tiktok.auth.key', '')
    #     app_secret = ir_config.get_param('tiktok.app.secret', '')
    #     url = 'https://auth-sandbox.tiktok-shops.com/api/v2/token/get?app_key=' + app_key + '&auth_code=' + auth_code + '&app_secret=' + app_secret + '&grant_type=authorized_code'
    #     req = requests.get(url).json()
    #     if req['code'] == 0:
    #         search_token = self.sudo().search([('token', '!=', None)], limit=1)
    #         if not search_token:
    #             self.env['base.integrate.tiktok'].sudo().create({
    #                 'token': req['data']['access_token'],
    #             })
    #         else:
    #             search_token.sudo().write({
    #                 'token': req['data']['access_token']
    #             })
    #         access_token = req['data']['access_token']
    #     else:
    #         access_token = self.sudo().search([]).token
    #     return access_token

    def get_sign_tiktok(self, url_api, parameter=None):
        if parameter is None:
            parameter = {}
        ir_config = self.env['ir.config_parameter'].sudo()
        secret = ir_config.get_param('tiktok.app.secret', '')
        app_key = ir_config.get_param('tiktok.app.key', '')
        ###time stamp config
        time_now = fields.Datetime.now()
        ###time stamp config
        current_gmt = time.gmtime()
        ##
        check_time_stamps = self.env['ir.config_parameter'].sudo().get_param('tiktok.time_stamp', 'False')
        ##
        if check_time_stamps != 'False':
            time_stamp = str(int(round(time_now.timestamp())))
        else:
            time_stamp = str(calendar.timegm(current_gmt))
        parameters = {"app_key": app_key, "timestamp": time_stamp}
        parameters.update(parameter)
        sort_dict = sorted(parameters)
        parameters_str = "%s%s" % (url_api, str().join('%s%s' % (key, parameters[key]) for key in sort_dict))
        signstring = secret + parameters_str + secret

        sign = hmac.new(secret.encode("utf-8"), signstring.encode("utf-8"), hashlib.sha256).hexdigest()
        return sign, time_stamp

    def _post_data_tiktok(self, url_api, data=None, files=None, param=None, headers=None):
        if param is None:
            param = {}
        ir_config = self.env['ir.config_parameter'].sudo()
        tiktok_url = ir_config.get_param('tiktok.api_url', '')
        app_key = ir_config.get_param('tiktok.app.key', '')
        access_token = self.env['ir.config_parameter'].sudo().get_param('tiktok.access_token', '')
        sign, ts = self.env['base.integrate.tiktok'].get_sign_tiktok(url_api)
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo'
            }
        data = data or dict()
        params = {"app_key": app_key,
                  "access_token": access_token,
                  "sign": sign,
                  "timestamp": ts,
                  }
        url = tiktok_url + url_api
        res = requests.post(
            url,
            data=data,
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        return res

    def _get_data_tiktok(self, url_api, data=None, files=None, param=None, headers=None):
        if param is None:
            param = {}
        ir_config = self.env['ir.config_parameter'].sudo()
        tiktok_url = ir_config.get_param('tiktok.api_url', '')
        app_key = ir_config.get_param('tiktok.app.key', '')
        access_token = self.env['ir.config_parameter'].sudo().get_param('tiktok.access_token', '')
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo'
            }
        sign, ts = self.get_sign_tiktok(url_api, parameter=param)
        params = {"app_key": app_key,
                  "access_token": access_token,
                  "sign": sign,
                  "timestamp": ts,
                  }
        params.update(param)

        url = tiktok_url + url_api
        data = data or dict()
        res = requests.get(
            url,
            data=data,
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        return res

    def _put_data_tiktok(self, url_api, data=None, files=None, param=None, headers=None):
        if param is None:
            param = {}
        ir_config = self.env['ir.config_parameter'].sudo()
        tiktok_url = ir_config.get_param('tiktok.api_url', '')
        app_key = ir_config.get_param('tiktok.app.key', '')
        access_token = self.env['ir.config_parameter'].sudo().get_param('tiktok.access_token', '')
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo'
            }
        data = data or dict()
        sign, ts = self.get_sign_tiktok(url_api, parameter=param)
        params = {"app_key": app_key,
                  "access_token": access_token,
                  "sign": sign,
                  "timestamp": ts,
                  }
        params.update(param)
        url = tiktok_url + url_api
        _logger.info('start check sync_stock_tiktok')
        _logger.info(url)
        _logger.info(data)
        _logger.info(params)
        _logger.info('end check sync_stock_tiktok')
        res = requests.put(
            url,
            data=data,
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        return res

    def get_warehouse_tiktok(self):
        url_api = '/api/logistics/get_warehouse_list'
        req = self.env['base.integrate.tiktok']._get_data_tiktok(url_api=url_api)
        if req.status_code == 200:
            return req
