import time
from datetime import date, timedelta, datetime

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import ValidationError, _logger
import requests
from odoo.tests import Form
import json


class AuthorizeTiktok(http.Controller):
    @http.route('/tiktok/callback', type='http', auth='public', methods=["GET"], csrf=False)
    def get_callback_tiktok_url(self, **kw):
        try:
            app_key = request.env['ir.config_parameter'].sudo().get_param('tiktok.app.key', '')
            app_secret = request.env['ir.config_parameter'].sudo().get_param('tiktok.app.secret', '')
            tiktok_mode = request.env['ir.config_parameter'].sudo().get_param('tiktok.tiktok_mode')
            url = ""
            if tiktok_mode == "sandbox":
                url = "{tiktok_oauth}/api/v2/token/get".format(
                    tiktok_oauth=request.env['ir.config_parameter'].sudo().get_param('tiktok.api_url_oauth'))
            elif tiktok_mode in ["service_none_us", "service_us"]:
                url = "{tiktok_oauth}/api/v2/token/get".format(tiktok_oauth="https://auth.tiktok-shops.com")
            params = dict(
                app_key=app_key,
                auth_code=kw['code'],
                app_secret=app_secret,
                grant_type='authorized_code'
            )
            if len(url) > 0:
                res = requests.get(
                    url=url,
                    params=params
                ).json()
                if res.get('code') == 0:
                    access_token_tiktok = res['data'].get('access_token', '')
                    request.env['ir.config_parameter'].sudo().set_param('tiktok.access_token', access_token_tiktok)
                    request.env['ir.config_parameter'].sudo().set_param('tiktok.refresh_token',
                                                                        res['data'].get('refresh_token', ''))
                    request.env['ir.config_parameter'].sudo().set_param('tiktok.access_token_expire_in',
                                                                        res['data'].get('access_token_expire_in', ''))
                    request.env['ir.config_parameter'].sudo().set_param('tiktok.connect_date', date.today())
                    request.env['ir.config_parameter'].sudo().set_param('tiktok.is_connect', True)
                    return request.redirect(
                        request.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/web")
                else:
                    request.env['ir.logging'].sudo().create({
                        'name': '#Tiktok: get_callback_tiktok_url',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': res.get('message'),
                        'func': 'get_callback_tiktok_url',
                        'line': '0',
                    })
                    return request.env['ir.ui.view'].with_context(rendering_bundle=True)._render_template(
                        'advanced_integrate_tiktok.s_template_connect_tiktok_fail')
            else:
                request.env['ir.logging'].sudo().create({
                    'name': '#Tiktok: get_callback_tiktok_url',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': "chưa có url or chua chọn tiktok_mode",
                    'func': 'get_callback_tiktok_url',
                    'line': '0',
                })
        except Exception as e:
            _logger.error('Can not connect Tiktok from params')
            raise ValidationError(e.args)

    @http.route('/boo', type='json', auth='none', methods=['POST'], csrf=False)
    def get_webhook_url(self, **kw):
        request.env.uid = SUPERUSER_ID
        payload = json.loads(request.httprequest.data)
        _logger.info('start check webhook_tiktok_order')
        _logger.info('/boo')
        _logger.info(payload)
        _logger.info('end check webhook_tiktok_order')
        try:
            is_connected = request.env['ir.config_parameter'].sudo().get_param('tiktok.is_connect', 'False')
            if is_connected == 'True':
                # payload = json.loads(request.httprequest.data)
                if payload:
                    if payload.get('type') and payload.get('type') in [1, 2]:
                        vals = {
                            's_mkp_payload': payload,
                            's_mkp_order_id': payload.get('data').get('order_id'),
                            's_is_mkp_tiktok': True
                        }
                        request.env['s.mkp.order.queue'].sudo().create(vals)
            return 200
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': '#Tiktok: get_webhook_url',
                'type': 'server',
                'dbname': 'OdooBoo',
                'level': '4',
                'path': 'url',
                'message': str(e) + str(payload),
                'func': 'get_webhook_url',
                'line': '0',
            })
            raise ValidationError(str(e))



