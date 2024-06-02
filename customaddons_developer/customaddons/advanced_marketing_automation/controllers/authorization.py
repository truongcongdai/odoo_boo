from odoo import http
from odoo.http import request
import requests

class AuthorizationZalo(http.Controller):
    @http.route('/zalo_verifierQTEU3PVQ4muTtiW8tSDv12Z7oIR4kHbwCJa.html', type='http', auth='public', methods=["GET"], csrf=False)
    def verifier(self, **kw):
        f = open("zalo_verifierQTEU3PVQ4muTtiW8tSDv12Z7oIR4kHbwCJa.html", "r")
        return f.read()

    @http.route('/authorization_oa_zalo', type='http', auth='public', methods=["GET"], csrf=False)
    def authorization_zalo(self, **kw):
        ir_config_param_obj = request.env['ir.config_parameter'].sudo()
        url = 'https://oauth.zaloapp.com/v4/oa/access_token'
        params = {'app_id':  ir_config_param_obj.get_param('integrate_zalo.app_id'),
                  'grant_type': 'authorization_code',
                  'code': kw['code']
                  }
        headers = {'secret_key': ir_config_param_obj.get_param('integrate_zalo.app_secret')}
        res = requests.post(url,
                           data={},
                           params = params,
                           headers = headers,
                           verify=False
                           )
        if res.status_code == 200:
            res_data = res.json()
            ir_config_param_obj.set_param('integrate_zalo.access_token', res_data['access_token'])
            ir_config_param_obj.set_param('integrate_zalo.refresh_token', res_data['refresh_token'])
            ir_config_param_obj.set_param('integrate_zalo.expires_in', res_data['expires_in'])
            ir_config_param_obj.set_param('integrate_zalo.is_connected_zalo', True)
            return ("Kết nối thành công")
        else:
            return ("Kết nối thất bại")

