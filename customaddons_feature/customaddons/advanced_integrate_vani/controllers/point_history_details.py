from odoo import http
from odoo.http import request
import json
from datetime import timedelta
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token
from odoo.addons.advanced_integrate_magento.tools.common import invalid_response
from datetime import datetime
import pytz

class PointsHistoryDetailsVani(http.Controller):
    @validate_integrate_token
    @http.route('/points-history-details', type='json', auth='none', methods=['POST'], csrf=False)
    def points_history_details(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data)
            if not body.get('customerId'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "customerId is mandatory"}
            if not body.get('limitDataCount'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "limitDataCount is mandatory"}
            if int(body.get('limitDataCount')) > 100:
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "limitDataCount maximum is 100"}
            if int(body.get('customerId')):
                customer_id = request.env['res.partner'].sudo().search([('id', '=', int(body.get('customerId')))], limit=1)
                if not customer_id:
                    return {"api_vani": True, "message": "Customer may not exits!"}
                if not customer_id.is_connected_vani:
                    return {"api_vani": True, "message": "Customer not registration!"}

                if customer_id.is_connected_vani:
                    result_message = []
                    count = 0
                    history_points_ids = request.env['s.order.history.points'].sudo().search([('res_partner_id', '=', customer_id.id)], limit=100)
                    for history_line in history_points_ids[::-1]:
                        if (history_line.order_id and not history_line.is_bill) or history_line.sale_order_id:
                            if history_line.order_id:
                                tz = pytz.utc.localize(history_line.order_id.date_order).astimezone(
                                    pytz.timezone('Asia/Ho_Chi_Minh'))
                            else:
                                tz = pytz.utc.localize(history_line.create_date).astimezone(
                                    pytz.timezone('Asia/Ho_Chi_Minh'))
                            transactionTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
                            # Giới hạn bản ghi theo limitDataCount
                            if len(result_message) < int(body.get('limitDataCount')):
                                # Tìm kiếm những đơn hàng POS được scan Vanila Barcode
                                if history_line.order_id or history_line.sale_order_id:
                                    count += 1
                                    # transactionStatus = None
                                    pointType = 'EARN'
                                    if history_line.diem_cong < 0:
                                        if history_line.sale_order_id:
                                            if history_line.sale_order_id.return_order_id:
                                                if len(result_message) > 0:
                                                    for result in result_message:
                                                        if result.get('transactionId') and int(result.get(
                                                                'transactionId')) == history_line.sale_order_id.return_order_id.id:
                                                                pass
                                                            # result.update({
                                                            #     'transactionStatus': 'CANCELLATION'
                                                            # })

                                                # transactionStatus = 'CANCELLATION'
                                        elif history_line.order_id:
                                            #check refund ca order
                                            is_cancel = False
                                            cancel_order = history_line.order_id.lines.filtered(lambda l: l.product_id.detailed_type == 'product' and l.qty > 0)
                                            if len(cancel_order)==0:
                                                if len(history_line.order_id.refunded_order_ids)>0:
                                                    total_refunded_order = sum(history_line.order_id.refunded_order_ids[0].lines.filtered(lambda l: l.product_id.detailed_type == 'product').mapped('qty'))
                                                    qty_total_refund_order = sum(history_line.order_id.lines.filtered(lambda l: l.product_id.detailed_type == 'product').mapped('qty'))
                                                    if abs(total_refunded_order)==abs(qty_total_refund_order):
                                                        is_cancel=True
                                                # elif history_line.order_id.sale_order_count >0:
                                                #     sale_order_id = history_line.order_id.lines.filtered(lambda l: l.sale_order_origin_id)
                                                #     total_refunded_sale_order = sum(
                                                #         history_line.order_id.refunded_order_ids[0].lines.filtered(
                                                #             lambda l: l.product_id.detailed_type == 'product').mapped(
                                                #             'qty'))
                                                #     qty_total_refund_order = sum(history_line.order_id.lines.filtered(
                                                #         lambda l: l.product_id.detailed_type == 'product').mapped(
                                                #         'qty'))
                                                #     if abs(total_refunded_order) == abs(qty_total_refund_order):
                                                #         is_cancel = True
                                            if history_line.order_id.is_cancel_order or is_cancel:
                                                # is_cancel = False
                                                # if history_line.order_id.refunded_orders_count > 0:
                                                #     total_refunded_order =history_line.order_id.refunded_order_ids[0].lines.filter(lambda l: l.product_id.detailed_type == 'product')
                                                #
                                                #     qty_total_refund_order = sum(history_line.order_id.order_id.lines.filter(lambda l: l.product_id.detailed_type == 'product').mapped('qty'))
                                                #     if abs(qty_total_refunded_order)==qty_total_refund_order:
                                                #         is_cancel=True
                                                # if history_line.order_id.sale_order_count > 0:
                                                #     if len(result_message) > 0:
                                                #         for result in result_message:
                                                #             if result.get('transactionId'):
                                                #                 if history_line.order_id.sale_order_count > 0:
                                                #                     sale_order_id = history_line.order_id.lines.filtered(lambda l: l.sale_order_origin_id)
                                                #                     if int(result.get('transactionId')) == sale_order_id[0].sale_order_origin_id.id:
                                                #                         result.update({
                                                #                             'transactionStatus': 'CANCELLATION'
                                                #                         })
                                                # if history_line.order_id.is_cancel_order or is_cancel:
                                                # if len(result_message) > 0:
                                                #     for result in result_message:
                                                #         if result.get('transactionId'):
                                                if len(history_line.order_id.refunded_order_ids)>0:
                                                    order_info = {
                                                        'transactionId': str(transactionId),
                                                        'pointType': 'CANCEL_EARN',
                                                        # 'transactionStatus': transactionStatus,
                                                        'transactionTime': transactionTime,
                                                        'where': where,
                                                        'pointAmount': abs(history_line.diem_cong),
                                                    }
                                                    result_message.append(order_info)
                                            else:
                                                # transactionStatus = 'APPROVAL'
                                                if history_line.order_id:
                                                    transactionId = history_line.order_id.id
                                                    where = history_line.order_id.pos_name
                                                else:
                                                    transactionId = history_line.sale_order_id.id
                                                    # where = history_line.sale_order_id.pos_name if history_line.sale_order_id else 'Online'
                                                    where = 'Online'
                                                order_info = {
                                                    'transactionId': str(transactionId),
                                                    'pointType': 'CANCEL_EARN',
                                                    # 'transactionStatus': transactionStatus,
                                                    'transactionTime': transactionTime,
                                                    'where': where,
                                                    'pointAmount': abs(history_line.diem_cong),
                                                }
                                                result_message.append(order_info)

                                    else:
                                        # transactionStatus = 'APPROVAL'
                                        pass

                                    if history_line.diem_cong > 0:
                                        if history_line.order_id:
                                            transactionId = history_line.order_id.id
                                            where = history_line.order_id.pos_name
                                        else:
                                            transactionId = history_line.sale_order_id.id
                                            where = 'Online'
                                        order_info = {
                                            'transactionId': str(transactionId),
                                            'pointType': pointType,
                                            # 'transactionStatus': transactionStatus,
                                            'transactionTime': transactionTime,
                                            'where': where,
                                            'pointAmount': abs(history_line.diem_cong),
                                        }
                                        result_message.append(order_info)

                return {
                    "api_vani": True,
                    "pointHistoryList": list(reversed(result_message)),
                }
        except Exception as e:
            return invalid_response(head='provided_data_failures', message=e.args)
