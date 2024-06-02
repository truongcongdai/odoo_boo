import datetime
from functools import wraps
import json
from odoo import SUPERUSER_ID
from odoo.http import request
from datetime import datetime


def validate_integrate_token(func):
    """
    Wrapper function for validating user api token

    @code: python
    import json
    import requests

    url = '...'
    resp_1 = requests.get(url, headers={'content-type': 'application/json', 'access_token': '...'}, json={})
    resp_2 = requests.post(url, headers={'content-type': 'application/json', 'access_token': '...'}, json={})
    resp_3 = requests.post(url, headers={'content-type': 'application/json', 'access_token': '...'},
                           data=json.dumps({}))
    resp_4 = requests.get(url, headers={'content-type': 'application/json', 'access_token': '...'},
                          params={}, json={})
    @return: <status_code 400> - case bad request
             <status_code 401> - no token found
             <status_code 403> - wrong token
             <status_code 500> - odoo internal error
             <status_code 200> - json response
    """

    @wraps(func)
    def wrap(self, *args, **kwargs):
        token_tiktok = self.env['base.integrate.tiktok'].sudo().get_warehouse_tiktok()
        str_access_token_expire_in = self.env['ir.config_parameter'].sudo().get_param('tiktok.access_token_expire_in')
        time_access_token_expire_in = datetime.fromtimestamp(int(str_access_token_expire_in))
        if time_access_token_expire_in < datetime.now() or token_tiktok is None:
            self.env['res.config.settings'].refresh_token()
        return func(self, *args, **kwargs)
    return wrap


def _create_log(*, name, message, func='validate_integrate_token'):
    return request.env['ir.logging'].sudo().create({
        'name': name,
        'type': 'server',
        'dbname': 'boo',
        'level': 'ERROR',
        'message': message,
        'path': request.httprequest.base_url,
        'func': func,
        'line': '0',
    })
