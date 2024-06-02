from odoo import http
from odoo.http import request
import json
from odoo import SUPERUSER_ID
from datetime import date, timedelta, datetime
from odoo.http import request, _logger
from odoo.exceptions import ValidationError


class AdvancedIntegrateSaleOrderLazada(http.Controller):
    """
    message_type: 0 Webhook Order status
    message_type: 14 - Webhook Fulfillment Order DO status
    message_type: 10 - Webhook API Reverse Order
    """

    @http.route('/sale-order-lazada-status', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_url(self, *args, **kwargs):
        is_connected_lazada = request.env['ir.config_parameter'].sudo().get_param('intergrate_lazada.is_connected_lazada')
        if is_connected_lazada:
            data = json.loads(request.httprequest.data)
            request.env.uid = SUPERUSER_ID
            _logger.info('start_check_webhook sale-order-lazada-status')
            _logger.info(data)
            _logger.info('end_check_webhook sale-order-lazada-status')
            if data and data.get('data'):
                # fulfillment_package_id khi hoan thanh don hang
                if data['message_type'] == 0:
                    if 'order_status' in data['data']:
                        try:
                            order_id = request.env['sale.order'].sudo().search(
                                [('is_lazada_order', '=', True), ('lazada_order_id', '=', data['data']['trade_order_id'])],
                                limit=1)
                            # update status order
                            if len(order_id) > 0:
                                # Status order
                                request.env['sale.order'].build_order_lazada(order_id, data)
                            else:
                                try:
                                    # create Order Lazada
                                    order_id = request.env['sale.order'].sync_order_lazada(data)
                                    if len(order_id) > 0:
                                        request.env['sale.order'].build_order_lazada(order_id, data)
                                    # if data['data']['order_status'] in ['unpaid', 'pending']:
                                    #
                                    # else:
                                    #     request.env['s.lazada.queue'].sudo().create({
                                    #         'dbname': 'boo',
                                    #         'level': 'order_error',
                                    #         'message': 'Lazada order do not exist',
                                    #         's_lazada_id_order': data['data'].get('trade_order_id'),
                                    #         'order_status': data['data'].get('order_status'),
                                    #         'data': data
                                    #     })
                                except Exception as e:
                                    request.env['s.lazada.queue'].sudo().create({
                                        'dbname': 'boo',
                                        'level': 'order_error',
                                        'message': str(e),
                                        's_lazada_id_order': data.get('data').get('trade_order_id'),
                                        'order_status': data.get('data').get('order_status'),
                                        'data': data
                                    })
                        except Exception as e:
                            request.env['s.lazada.queue'].sudo().create({
                                'dbname': 'boo',
                                'level': 'status_error',
                                'message': str(e),
                                's_lazada_id_order': data.get('data').get('trade_order_id'),
                                'order_status': data.get('data').get('order_status'),
                                'data': data
                            })
                # Reverse Order status - Hoan tien va hoan hang
                # elif data['message_type'] == 10:
                #     if data.get('data').get('reverse_status'):
                #         order_id = request.env['sale.order'].sudo().search(
                #             [('is_lazada_order', '=', True),
                #              ('lazada_order_id', '=', data.get('data').get('trade_order_id'))],
                #             limit=1)
                #         if data.get('data').get('reverse_status') in 'RTM_RECEIVE_ITEM':
                #             self.create_so_return(data, order_id)
                # Status DO
                elif data['message_type'] == 14:
                    if 'status' in data['data']:
                        order_id_shipment = request.env['sale.order'].sudo().search(
                            [('is_lazada_order', '=', True), ('lazada_order_id', '=', data['data']['trade_order_id'])])
                        picking_ids = order_id_shipment.picking_ids
                        if picking_ids:
                            for picking_id in picking_ids:
                                if not picking_id.is_do_lazada_return:
                                    picking_id.sudo().picking_lazada_status = data['data']['status'].lower()
