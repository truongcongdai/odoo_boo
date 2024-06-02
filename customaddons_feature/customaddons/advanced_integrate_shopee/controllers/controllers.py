from datetime import date
from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import ValidationError, _logger
import requests
import hashlib
import hmac
import time
from odoo.tests import Form
import json
from odoo.addons.mail.controllers.discuss import DiscussController
import urllib3
from datetime import date, timedelta, datetime

urllib3.disable_warnings()


class AdvancedShopeeController(http.Controller):

    @http.route('/shopee/callback', type='http', auth='public', methods=["GET"], csrf=False)
    def get_callback_shopee_url(self, **kw):
        try:
            ir_config = request.env['ir.config_parameter'].sudo()
            host = ir_config.get_param('advanced_integrate_shopee.shopee_url', '')
            auth_code_shopee = kw.get('code')
            shop_id = kw.get('shop_id')
            app_key_shopee = ir_config.get_param('advanced_integrate_shopee.shopee_app_key', '')
            app_secret_shopee = ir_config.get_param('advanced_integrate_shopee.shopee_app_secret', '')
            timest = int(time.time())
            path = "/api/v2/auth/token/get"
            body = {"code": auth_code_shopee, "shop_id": int(shop_id), "partner_id": int(app_key_shopee)}
            tmp_base_string = "%s%s%s" % (app_key_shopee, path, timest)
            base_string = tmp_base_string.encode()
            partner_key = app_secret_shopee.encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            url = host + path + "?partner_id=%s&timestamp=%s&sign=%s" % (app_key_shopee, timest, sign)
            headers = {"Content-Type": "application/json", "User-Agent": "Odoo"}
            res = requests.post(url, json=body, headers=headers)
            if 'access_token' in res.json():
                access_token_shopee = res.json().get('access_token', '')
                request.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.access_token_shopee',
                                                                    access_token_shopee)
                request.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.shopee_expire_in',
                                                                    res.json().get('expire_in'))
                request.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.shopee_shop_id',
                                                                    kw.get('shop_id'))
                request.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.refresh_token_shopee',
                                                                    res.json().get('refresh_token'))
                request.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.shopee_connected_date',
                                                                    date.today())
                request.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.is_connect_shopee', True)
                request.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.is_error_token_shopee',
                                                                    'False')
                return request.redirect(request.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/web")
            else:
                request.env['ir.logging'].sudo().create({
                    'name': 'Connect_Odoo_Shope',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': res.json().get('error'),
                    'func': 'get_callback_shopee_url',
                    'line': '0',
                })
                return ("Kết nối thất bại")
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'Connect_Odoo_Shope',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'get_callback_shopee_url',
                'line': '0',
            })

    @http.route('/webhook/order/shopee', type='json', auth='none', methods=['POST'], csrf=False)
    def get_webhook_order_shopee(self, **kw):
        payload = json.loads(request.httprequest.data)
        request.env.uid = SUPERUSER_ID
        code = payload.get('code')
        _logger.info('start check webhook_shopee_order')
        _logger.info('/webhook/order/shopee')
        _logger.info(payload)
        _logger.info('end check webhook_shopee_order')
        """
        code=3: Order status push
        code=4: Order tracking no push
        code=15: shipping_document_status_push
        """
        if code in [3, 4, 15]:
            try:
                is_connect_shopee = request.env['ir.config_parameter'].sudo().get_param(
                    'advanced_integrate_shopee.is_connect_shopee')
                if is_connect_shopee:
                    if payload.get('data'):
                        data = payload.get('data')
                        if data.get('ordersn'):
                            ordersn = data.get('ordersn')
                            # create queue mkp order
                            vals = {
                                's_wh_code': code,
                                's_mkp_payload': payload,
                                's_mkp_order_id': ordersn,
                                's_is_mkp_shopee': True
                            }
                            request.env['s.mkp.order.queue'].sudo().create(vals)
                        else:
                            request.env['s.sale.order.shopee.error'].sudo().create({
                                'dbname': 'boo',
                                'level': 'STATUS_ERROR',
                                'message': " ordersn not in data, payload: %s" % str(payload),
                                'payload': str(payload),
                            })
                    else:
                        request.env['s.sale.order.shopee.error'].sudo().create({
                            'dbname': 'boo',
                            'level': 'STATUS_ERROR',
                            'message': "data not in payload, payload: %s" % str(payload),
                            'payload': str(payload),
                        })
                return 200
            except Exception as e:
                request.env['ir.logging'].sudo().create({
                    'name': '#Shopee: get_webhook_order_shopee',
                    'type': 'server',
                    'dbname': 'OdooBoo',
                    'level': '4',
                    'path': 'url',
                    'message': str(e) + str(payload),
                    'func': 'get_webhook_order_shopee',
                    'line': '0',
                })
                raise ValidationError(str(e))
