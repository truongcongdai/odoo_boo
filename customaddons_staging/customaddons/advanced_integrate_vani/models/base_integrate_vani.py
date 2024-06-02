from odoo import models, _
import requests
import logging
import json
import jwt
_logger = logging.getLogger(__name__)
from odoo.tools import date_utils
from odoo.http import Response, JsonRequest
from odoo import http


class BaseIntegrateVani(models.Model):
    _name = 'base.integrate.vani'

    def _post_data_vani(self, url, command, data=None, headers=None):
        api_key = self.env['ir.config_parameter'].sudo().get_param('vani.api.key', '')
        url = url
        if headers == None:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer %s' % (api_key,),
            }
        try:
            headers.update({'User-Agent': 'Odoo'})
        except Exception as e:
            _logger.debug("USER_AGENT Error: %r", e)
        data = data or dict()
        res = requests.post(
            url,
            data=data,
            headers=headers,
            verify=False
        )
        if res.status_code != 200:
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': res.text + str(data),
                'path': url,
                'func': '_post_data_vani',
                'line': '0',
            })
        else:
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'message': res.text + str(data),
                'path': url,
                'func': '_post_data_vani',
                'line': '0',
            })
        return res

    def _generate_request_token_jwt(self, payload):
        api_key = self.env['ir.config_parameter'].sudo().get_param('vani.api.key', '')
        encode_data = jwt.encode(payload=payload, key=api_key, algorithm="HS512")
        return encode_data

class JsonRequestNew(JsonRequest):
    def _json_response(self, result=None, error=None):
        responseData = super(JsonRequestNew, self)._json_response(result=result, error=error)
        # if 'api_vani' in result.keys():
        is_error_api_error=False
        if result and type(result) == dict and result.get('api_vani', ''):
            response = {}
            if error is not None:
                response = error
            if result is not None:
                result.pop('api_vani')
                response = result
            if response.get('errorCode') in ('DUP_EMAIL','DUP_BARCODE','DUP_PHONE','INSUFFICIENT_PARAMTER',):
                is_error_api_error = True
        else:
            response = {
                'jsonrpc': '2.0',
                'id': self.jsonrequest.get('id')
            }
            if error is not None:
                response['error'] = error
            if result is not None:
                response['result'] = result
        mime = 'application/json'
        body = json.dumps(response, default=date_utils.json_default)
        if is_error_api_error:
            return Response(
                body, status=400,
                headers=[('Content-Type', mime), ('Content-Length', len(body))]
            )
        else:
            # if self.httprequest.path == '/sale-order-lazada-status':
            #     body = {
            #         'status': 200
            #     }
            #     return Response(
            #         json.dumps(body), status=error and error.pop('http_status', 404) or 200,
            #         headers=[('Content-Type', mime), ('Content-Length', 0)]
            #     )
            return Response(
                body, status=error and error.pop('http_status', 404) or 200,
                headers=[('Content-Type', mime), ('Content-Length', len(body))]
            )


class RootNew(http.Root):
    def get_request(self, httprequest):
        # deduce type of request
        jsonResponse = super(RootNew, self).get_request(httprequest=httprequest)
        if httprequest.mimetype in ("application/json", "application/json-rpc"):
            return JsonRequestNew(httprequest)
        else:
            return jsonResponse
http.root = RootNew()
