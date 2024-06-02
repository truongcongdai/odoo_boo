from datetime import date
from odoo import http, SUPERUSER_ID
from odoo.http import request
from werkzeug.wrappers import Response
import json
import webbrowser
import datetime as date
from datetime import datetime

import urllib3

urllib3.disable_warnings()


class SZaloMiniAppController(http.Controller):

    @http.route('/zalo_mini_app/point_exchange_history', type='http', auth='public', methods=['POST'], csrf=False)
    def zalo_mini_app_point_exchange_history(self, **kwargs):
        uid = "6817823554872742467"
        partner_id = request.env['res.partner'].sudo().search([('s_zalo_sender_id', '=', uid)], limit=1)
        response = []
        if partner_id:
            history_points_ids = partner_id.history_points_ids
            if history_points_ids:
                for history_points_id in history_points_ids:
                    date_and_code_order, code_orders = "", ""
                    content = "Quy đổi điểm tại" if history_points_id.diem_cong < 0 else "Tích điểm tại"
                    if history_points_id.order_id:
                        if "Đơn hàng " in history_points_id.order_id.display_name:
                            code_orders = history_points_id.order_id.display_name.replace('Đơn hàng ', '#')
                        elif "Order" in history_points_id.order_id.display_name:
                            code_orders = history_points_id.order_id.display_name.replace('Order ', '#')
                        date_order = history_points_id.order_id.date_order.strftime('%d/%m/%Y')
                        date_and_code_order = date_order + ' | ' + code_orders
                    elif history_points_id.sale_order_id:
                        if not history_points_id.sale_order_id.is_return_order:
                            if history_points_id.sale_order_id.is_magento_order:
                                if history_points_id.sale_order_id.m2_so_id:
                                    code_orders = "#" + str(history_points_id.sale_order_id.m2_so_id)
                            elif history_points_id.sale_order_id.is_tiktok_order:
                                if history_points_id.sale_order_id.tiktok_order_id:
                                    code_orders = "#" + str(history_points_id.sale_order_id.tiktok_order_id)

                            elif history_points_id.sale_order_id.is_lazada_order:
                                if history_points_id.sale_order_id.lazada_order_id:
                                    code_orders = "#" + str(history_points_id.sale_order_id.lazada_order_id)

                            elif history_points_id.sale_order_id.s_shopee_is_order:
                                if history_points_id.sale_order_id.s_shopee_id_order:
                                    code_orders = "#" + str(history_points_id.sale_order_id.s_shopee_id_order)

                        else:
                            if history_points_id.sale_order_id.return_order_id:
                                if history_points_id.sale_order_id.return_order_id:
                                    if history_points_id.sale_order_id.return_order_id.m2_so_id:
                                        code_orders = "#" + str(history_points_id.sale_order_id.return_order_id.m2_so_id)
                            elif history_points_id.sale_order_id.tiktok_reverse_order_id:
                                code_orders = "#" + str(history_points_id.sale_order_id.tiktok_reverse_order_id)
                            elif history_points_id.sale_order_id.reverse_order_id:
                                code_orders = "#" + str(history_points_id.sale_order_id.reverse_order_id)
                            elif history_points_id.sale_order_id.s_shopee_return_sn:
                                code_orders = "#" + str(history_points_id.sale_order_id.s_shopee_return_sn)

                        # if history_points_id.sale_order_id.is_return_order:
                        #     code_orders = "#" + history_points_id.sale_order_id.name.split("-")[0]
                        # else:
                        #     code_orders = "#" + history_points_id.sale_order_id.name
                        date_order = history_points_id.sale_order_id.date_order.strftime('%d/%m/%Y')
                        date_and_code_order = date_order + ' | ' + code_orders
                    if history_points_id.sale_order_id.is_ecommerce_order or history_points_id.sale_order_id.is_magento_order or history_points_id.sale_order_id.is_tiktok_order or history_points_id.sale_order_id.is_lazada_order or history_points_id.sale_order_id.s_shopee_is_order or history_points_id.sale_order_id.is_return_order or history_points_id.order_id:
                        param_response = {
                            "content": content if history_points_id.sale_order_id else content + "\n",
                            "name_pos": history_points_id.order_id.name if history_points_id.order_id else " Ecommerce",
                            "date_and_code_order": date_and_code_order,
                            # "order_id": history_points_id.order_id.pos_reference if history_points_id.order_id else "",
                            # "sale_order_id": history_points_id.sale_order_id.name if history_points_id.sale_order_id else "",
                            "diem_cong": "{:,}".format(history_points_id.diem_cong) if history_points_id else "",
                        }
                        response.append(param_response)
        request.env['ir.logging'].sudo().create({
            'name': '###Zalo_Mini_app: zalo_mini_app_point_exchange_history',
            'type': 'server',
            'dbname': 'boo',
            'level': 'info',
            'path': 'url',
            'message': "call vào",
            'func': 'zalo_mini_app_point_exchange_history',
            'line': '0',
        })
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Allow CORS for your specific origin
            'Access-Control-Allow-Methods': 'POST, OPTIONS, GET, PUT, DELETE',  # Allow the request methods
            'Access-Control-Allow-Headers': 'Content-Type, Accept, Authorization'  # Allow 'Content-Type' header
        }
        return request.make_response(json.dumps(response), headers)


