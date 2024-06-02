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
        token_shopee = request.env['s.base.integrate.shopee'].sudo().get_shop_info_shopee()
        str_access_token_expire_in = request.env['ir.config_parameter'].sudo().get_param(
            'advanced_integrate_shopee.shopee_expire_in')
        time_access_token_expire_in = datetime.fromtimestamp(str_access_token_expire_in)
        if token_shopee is None or time_access_token_expire_in < datetime.now():
            request.env['ir.config_parameter'].sudo().btn_refresh_token_shopee()
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
