from functools import wraps
import json
from odoo import SUPERUSER_ID
from odoo.http import request
from .common import invalid_response


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
        access_token = request.httprequest.args.get('access_token')
        if not access_token:
            basic_auth = request.httprequest.headers.get('Authorization')
            if basic_auth.split()[0] == 'Basic':
                access_token = basic_auth.split()[-1]
            else:
                # _create_log(message=json.dumps(request.httprequest.args), name='token_not_found')
                return invalid_response(head='token_not_found', message='Token is required for API calling!',
                                        status=401)
        token_for_integrate = request.env['ir.config_parameter'].sudo().get_param('integrate.token_for_integrate')
        if not token_for_integrate or token_for_integrate != access_token:
            # _create_log(message=access_token, name='token_mismatch')
            return invalid_response(head='token_mismatch', message='Token is wrong, can not give accessibility!',
                                    status=403)
        # region TODO: @nhatnm: the default @http.route does not return url query params, thus we have to do this trick
        # clear this next line if you find a better solution.
        kwargs.update(dict(request.httprequest.args))
        kwargs.pop('access_token', False)
        # endregion
        request.env.uid = SUPERUSER_ID
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
