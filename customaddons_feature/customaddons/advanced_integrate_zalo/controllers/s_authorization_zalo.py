from datetime import date
from odoo import http, SUPERUSER_ID
from odoo.http import request
import requests
import json
import datetime as date
from datetime import datetime

import urllib3

urllib3.disable_warnings()

class SAuthorizationZalo(http.Controller):

    @http.route('/zalo_verifierQTEU3PVQ4muTtiW8tSDv12Z7oIR4kHbwCJa.html', type='http', auth='public', methods=["GET"],
                csrf=False)
    def verifier(self, **kw):
        f = open("zalo_verifierQTEU3PVQ4muTtiW8tSDv12Z7oIR4kHbwCJa.html", "r")
        return f.read()

    @http.route('/authorization_oa_zalo', type='http', auth='public', methods=["GET"], csrf=False)
    def authorization_zalo(self, **kw):
        ir_config_param_obj = request.env['ir.config_parameter'].sudo()
        url = ir_config_param_obj.get_param('advanced_integrate_zalo.s_url_oauth')+'/oa/access_token'
        params = {'app_id': ir_config_param_obj.get_param('advanced_integrate_zalo.app_id'),
                  'grant_type': 'authorization_code',
                  'code': kw['code']
                  }
        headers = {'secret_key': ir_config_param_obj.get_param('advanced_integrate_zalo.app_secret')}
        res = requests.post(url,
                            data={},
                            params=params,
                            headers=headers,
                            verify=False
                            )
        if res.status_code == 200:
            res_data = res.json()
            ir_config_param_obj.set_param('advanced_integrate_zalo.access_token', res_data['access_token'])
            ir_config_param_obj.set_param('advanced_integrate_zalo.refresh_token', res_data['refresh_token'])
            ir_config_param_obj.set_param('advanced_integrate_zalo.expires_in', res_data['expires_in'])
            ir_config_param_obj.set_param('advanced_integrate_zalo.is_connected_zalo', True)
            request.env['ir.cron'].sudo().search([('cron_name', '=', '### Zalo: Refresh update token')]).write({
                "nextcall": datetime.now() + date.timedelta(seconds=int(res_data['expires_in']))
            })
            return request.redirect(request.env[
                'ir.config_parameter'].sudo().get_param('web.base.url')+ "/web")

        else:
            return ("Kết nối thất bại")
