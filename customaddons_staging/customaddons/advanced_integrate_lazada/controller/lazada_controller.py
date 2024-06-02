from odoo import http
from odoo.http import request
import time
import hmac
import hashlib
import requests


class AuthorizeLazada(http.Controller):
    @http.route('/authorization', type='http', auth='public', methods=["GET"], csrf=False)
    def integrating_lazada(self, **kw):
        ir_config_param_obj = request.env['ir.config_parameter'].sudo()
        timestamp = int(round(time.time() * 1000))
        api = "/auth/token/create"
        parameters = {"app_key":  ir_config_param_obj.get_param('intergrate_lazada.app_key'), "timestamp": timestamp, "code": kw['code'], "sign_method": "sha256"}
        sort_dict = sorted(parameters)
        parameters_str = "%s%s" % (api, str().join('%s%s' % (key, parameters[key]) for key in sort_dict))
        h = hmac.new(ir_config_param_obj.get_param('intergrate_lazada.app_secret').encode(encoding="utf-8"), parameters_str.encode(encoding="utf-8"),
                     digestmod=hashlib.sha256)
        sign = h.hexdigest().upper()
        parameters.update({"sign": sign})

        url = "https://auth.lazada.com/rest" + api
        res = requests.get(url,
                           data={},
                           params=parameters,
                           headers={},
                           verify=False)
        res_data = res.json()
        if res_data['code'] == '0':
            ir_config_param_obj.set_param('intergrate_lazada.access_token', res_data['access_token'])
            ir_config_param_obj.set_param('intergrate_lazada.refresh_token', res_data['refresh_token'])
            ir_config_param_obj.set_param('intergrate_lazada.is_connected_lazada', True)
            return request.redirect(request.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/web")
        else:
            return ("Kết nối thất bại")
