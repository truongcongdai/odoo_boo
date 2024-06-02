# -*- coding: utf-8 -*-
import datetime
import json
from odoo import http, SUPERUSER_ID, _
from odoo.http import request
from odoo.exceptions import ValidationError
from ..tools.api_wrapper import validate_integrate_token
from ..tools.common import invalid_response, valid_response
from odoo.addons.http_routing.models.ir_http import slugify_one


def _get_src_order(data):
    sale_order = sale_order_obj = request.env['sale.order'].sudo()
    channel_sale_mappings_obj = request.env['channel.order.mappings']
    sale_order_id = data
    external_id = data.pop('id', '')
    order_name = data.pop('order_name', '')
    if sale_order_id and isinstance(sale_order_id, int):
        sale_order = sale_order_obj.browse(sale_order_id)
    else:
        if external_id:
            sale_order = channel_sale_mappings_obj.search(
                [('store_order_id', '=', external_id)], limit=1
            ).order_name
    if not sale_order:
        sale_order = sale_order_obj.search([('name', '=', order_name)], limit=1)
    sale_order.ensure_one()
    return sale_order, data


class AdvancedIntegrateDeliveryOrderMagento(http.Controller):

    @staticmethod
    def _default_picking_type_id():
        delivery = request.env['stock.picking.type'].sudo().search([('code', '=', 'outgoing')], limit=1)
        if not delivery:
            raise ValidationError('delivery method not found!')
        return delivery.id

    @staticmethod
    def _format_picking(pickings):
        res = []
        pickings.invalidate_cache()
        for pick in pickings:
            res.append({
                'id': pick.id,
                'source_location': pick.location_id.name_get(),
                'destination_location': pick.partner_id.read(
                    ['street', 'street2', 'city', 'zip', 'state_id', 'country_id']
                ),
                'state': pick.state,
                'scheduled_date': pick.scheduled_date.isoformat(),
                'origin': pick.origin,
                'shipping_method': pick.carrier_id.name_get(),
                'operations': [{
                    'product': move.product_id.name_get(),
                    'demand_qty': move.product_uom_qty,
                    'reserved_qty': move.forecast_availability,
                } for move in pick.move_ids_without_package]
            })
        return res

    @staticmethod
    def _create_pick_mappings(*, action, picking_ids=[]):
        pick_mappings_obj = request.env['channel.pick.mappings'].with_user(SUPERUSER_ID)
        magento_sale_channel = request.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
        if not magento_sale_channel:
            raise ValidationError('Magento2x Sale Channel is not defined!')
        return pick_mappings_obj.create([{
            'channel_id': magento_sale_channel.id,
            'ecom_store': 'magento2x',
            'stock_picking_id': pick,
            'odoo_stock_picking_id': pick,
            'operation': action,
            'need_sync': 'no',
        } for pick in picking_ids])

    @staticmethod
    def _grooming_post_data(data):
        try:
            res = dict()
            if not isinstance(data, dict):
                data = json.loads(data)
            warehouse = warehouse_obj = request.env['stock.warehouse'].sudo()
            sale_order, data = _get_src_order(data)
            if not sale_order.is_magento_order:
                raise ValidationError('Sale order not comes from Magento, '
                                      'thus Magento should not create delivery orders from it!')
            res['magento_do_id'] = data.get('magento_do_id', 0)
            res['origin'] = sale_order.name
            res['sale_id'] = sale_order.id
            if not sale_order.partner_shipping_id:
                res['partner_id'] = sale_order.partner_id.id
            else:
                res['partner_id'] = sale_order.partner_shipping_id.id
            if data.get('scheduled_date', ''):
                res['scheduled_date'] = datetime.datetime.strptime(data['scheduled_date'], "%Y-%m-%dT%H:%M:%S")
            location_input = slugify_one(data.pop('source_location', '')).replace('-', '_')
            if isinstance(location_input, str):
                warehouse = warehouse_obj.search([('source_code_name', '=ilike', location_input)])
            if not warehouse:
                raise ValidationError('Source Location Input Wrong!')
            location = warehouse.lot_stock_id
            dest_loc_id = False
            picking_type_id = warehouse.out_type_id.id
            if warehouse.out_type_id.default_location_dest_id:
                dest_loc_id = warehouse.out_type_id.default_location_dest_id.id
            if not dest_loc_id:
                dest_loc_id = request.env['stock.location'].sudo().search(
                    [('usage', '=', 'customer')], limit=1
                ).id
            if not dest_loc_id:
                raise ValidationError('Delivery Location is not set!')
            res['location_id'] = location.id
            res['location_dest_id'] = dest_loc_id
            res['move_ids_without_package'] = [(5, 0, 0)]
            operations = data.pop('operations', [])
            procurement_group = sale_order.create_boo_api_procurement_group()
            for move in operations:
                product_id = move['product']
                product = request.env['product.product'].sudo().browse(product_id)
                demand_qty = move['demand_qty']
                sale_line_id_obj = sale_order.order_line.filtered(
                    lambda sol: sol.product_id.id == product_id and
                                sol.is_product_free == move.get('is_product_free', False) and not sol.is_product_reward)
                if sale_line_id_obj:
                    for line in sale_line_id_obj:
                        move_data = {
                            'product_id': product_id,
                            'name': product.display_name,
                            'product_uom_qty': demand_qty,
                            'product_uom': product.uom_id.id,
                            'sale_line_id': line.id,
                            'location_id': location.id,
                            'group_id': procurement_group.id,
                            'location_dest_id': dest_loc_id,
                            'is_product_free': line.is_product_free,
                        }
                        res['move_ids_without_package'].append((0, 0, move_data))

            product_shipping_method = sale_order.order_line.filtered(
                lambda p_ship: p_ship.is_delivery == True)
            picking_cancel = sale_order.picking_ids.filtered(lambda p_c: p_c.state == 'cancel')
            if product_shipping_method:
                if len(sale_order.picking_ids) == 0 or len(sale_order.picking_ids) == len(picking_cancel):
                    res['move_ids_without_package'].append((0, 0, {
                        'sale_line_id': product_shipping_method[0].id,
                        'product_id': product_shipping_method[0].product_id.id,
                        'name': product_shipping_method[0].name,
                        'product_uom': 1,
                        'location_id': location.id,
                        'group_id': procurement_group.id,
                        'location_dest_id': dest_loc_id
                    }))

                    if sale_order.s_facebook_sender_id or sale_order.s_zalo_sender_id:
                        carrier_id = request.env['delivery.carrier'].sudo().search(
                            [('name', 'ilike', product_shipping_method.product_id.name)],
                            limit=1)
                        res['carrier_id'] = carrier_id.id if carrier_id else False
            res['picking_type_id'] = picking_type_id
            return res
        except Exception as e:
            raise ValidationError(e.args)

    def _get_delivery_orders(self):
        picking_obj = request.env['stock.picking'].with_user(SUPERUSER_ID)
        picking_type_id = self._default_picking_type_id()
        pickings = picking_obj.search([('picking_type_id', '=', picking_type_id)])
        self._create_pick_mappings(action='export', picking_ids=pickings.ids)
        return self._format_picking(pickings)

    def _create_delivery_order(self):
        picking_obj = request.env['stock.picking'].with_user(SUPERUSER_ID)
        body = request.jsonrequest
        if body.get('magento_do_id'):
            pickings = picking_obj.search([('magento_do_id', '=', body.get('magento_do_id'))])
            if pickings:
                return self._format_picking(pickings)
        data = self._grooming_post_data(request.jsonrequest)
        picking = picking_obj.create(data)
        picking.action_confirm()
        self._create_pick_mappings(action='import', picking_ids=[picking.id])
        return self._format_picking(picking)

    def _get_delivery_order_by_id(self, order_id):
        picking_obj = request.env['stock.picking'].with_user(SUPERUSER_ID)
        picking = picking_obj.browse(order_id)
        if not picking.exists() or picking.picking_type_code != 'outgoing':
            raise ValidationError('Delivery order not exists!')
        self._create_pick_mappings(action='export', picking_ids=[picking.id])
        return self._format_picking(picking)

    def _edit_delivery_order_by_id(self, order_id):
        picking_obj = request.env['stock.picking'].with_user(SUPERUSER_ID)
        picking = picking_obj.browse(order_id)
        if not picking.exists() or picking.picking_type_code != 'outgoing':
            raise ValidationError('Delivery order not exists!')
        body = self._grooming_post_data(request.jsonrequest)
        picking.write(body)
        self._create_pick_mappings(action='import', picking_ids=[picking.id])
        return self._format_picking(picking)

    @validate_integrate_token
    @http.route(['/delivery-order'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def api_call_delivery_orders(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            if request.httprequest.method == 'GET':
                return self._get_delivery_orders()
            create_delivery_order = self._create_delivery_order()
            request.env['ir.logging'].sudo().create({
                'name': 'api-delivery-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(body) if body else None,
                'func': 'api_call_delivery_orders',
                'line': '0',
            })
            return create_delivery_order
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-delivery-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'api_call_delivery_orders',
                'line': '0',
            })
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/delivery-order/<int:order_id>', methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def api_call_delivery_order_by_id(self, order_id=None, *args, **kwargs):
        try:
            if request.httprequest.method == 'GET':
                get_do_by_id = self._get_delivery_order_by_id(order_id)
                request.env['ir.logging'].sudo().create({
                    'name': 'api-delivery-order-magento',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(get_do_by_id) if get_do_by_id else None,
                    'func': 'api_call_delivery_orders',
                    'line': '0',
                })
                return get_do_by_id
            edit_do_by_id = self._edit_delivery_order_by_id(order_id)
            request.env['ir.logging'].sudo().create({
                'name': 'api-delivery-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(edit_do_by_id) if edit_do_by_id else None,
                'func': 'api_call_delivery_orders',
                'line': '0',
            })
            return edit_do_by_id
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-delivery-order-update-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_call_delivery_order_update',
                'line': '0',
            })
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/cancel/delivery-order/<int:do_id>', methods=['POST'], auth='public', type='json', csrf=False)
    def api_call_cancel_delivery_order_by_id(self, do_id=None, *args, **kwargs):
        try:
            picking_obj = request.env['stock.picking'].with_user(SUPERUSER_ID)
            picking = picking_obj.browse(do_id)
            if not picking.exists():
                raise ValidationError('Delivery order not exists!')
            if picking.state != 'cancel':
                picking.with_context(api_cancel_do=True).action_cancel()
            return {
                'id': do_id,
                'magento_do_id': picking.magento_do_id,
                'state': picking.state
            }
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-cancel-delivery-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_call_cancel_delivery_orders',
                'line': '0',
            })
            return invalid_response(head='fail_action_api_call_cancel_delivery_order_by_id', message=e.args)

    def update_status_invoices(self, magento_do_id, shipment_status):
        try:
            do_id = request.env['stock.picking'].sudo().search([('magento_do_id', '=', magento_do_id)],
                                                               order='id desc', limit=1)
            invoice_id = request.env['account.move'].sudo().search([('magento_do_id', '=', magento_do_id)], limit=1)
            if do_id and do_id.sale_id.payment_method == 'cod':
                if shipment_status == "giao_hang_that_bai":
                    # do_id['shipment_status'] = 'giao_hang_that_bai'
                    # do_id.sale_id.write({
                    #     'shipment_status_date': datetime.datetime.now()
                    # })
                    if invoice_id:
                        if invoice_id.state == 'posted':
                            invoice_id.button_draft()
                        if invoice_id.state == 'draft':
                            invoice_id.button_cancel()
                        # return invoice_id.read(['name', 'state'])
                        return magento_do_id
                elif shipment_status == "da_giao_hang":
                    # do_id['shipment_status'] = 'giao_hang_thanh_cong'
                    # do_id.sale_id.write({
                    #     'shipment_status_date': datetime.datetime.now()
                    # })
                    if invoice_id:
                        if invoice_id.state == 'draft':
                            invoice_id.sudo().action_post()
                        invoice_id.sudo().action_direct_register_payment()
                        # return invoice_id.read(['name', 'state'])
                        return magento_do_id
            return magento_do_id
            # else:
            #     raise ValidationError('Payment method must be COD')
        except Exception as e:
            return invalid_response(head='fail_action_update_invoices_for_order', message=e.args)

    def shipment_status_fail(self, magento_do_id, shipment_status):
        do_id = request.env['stock.picking'].sudo().search([('magento_do_id', '=', magento_do_id)],
                                                           limit=1)
        if do_id:
            return_picking_old_id = do_id.sale_id.picking_ids.filtered(lambda p: do_id.name in p.origin)
            if return_picking_old_id:
                return_picking_old_id.sudo().write({
                    'is_boo_do_return': True
                })
            else:
                # Tao lenh return DO
                return_picking_id = request.env['stock.return.picking'].create({'picking_id': do_id.id})
                # Them san pham vao return DO
                return_picking_id.sudo()._onchange_picking_id()
                # tao phieu return DO
                if len(return_picking_id.product_return_moves) > 0:
                    result_return_picking = return_picking_id.sudo().create_returns()
                    if result_return_picking:
                        boo_do_return = request.env['stock.picking'].search(
                            [('id', '=', result_return_picking.get('res_id'))])
                        if boo_do_return and not boo_do_return.is_boo_do_return:
                            boo_do_return.write({'is_boo_do_return': True})
            if shipment_status == "giao_hang_that_bai":
                do_id.sudo().write({
                    'shipment_status': 'giao_hang_that_bai'
                })
            # Xu ly invoice cua DO
            result_update_status = self.update_status_invoices(magento_do_id, shipment_status)
            if result_update_status == magento_do_id:
                return {'magento_do_id': magento_do_id}
            else:
                return invalid_response(head='param_input_error')
        else:
            raise ValidationError('DO do not exist!')

    def shipment_status_success(self, magento_do_id, shipment_status):
        do_id = request.env['stock.picking'].sudo().search([('magento_do_id', '=', magento_do_id)],
                                                           limit=1)
        if do_id and shipment_status == "da_giao_hang":
            do_id.sudo().write({
                'shipment_status': 'giao_hang_thanh_cong'
            })
        status_invoices = self.update_status_invoices(magento_do_id, shipment_status)
        if status_invoices == magento_do_id:
            return {'magento_do_id': magento_do_id}
        else:
            return invalid_response(head='param_input_error')

    @validate_integrate_token
    @http.route('/shipment/update-status', methods=['POST'], auth='public', type='json', csrf=False)
    def update_shipment_status(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            if body.get('magento_shipment_status') == 'giao_hang_that_bai':

                shipment_status_fail = self.shipment_status_fail(body.get('magento_do_id'),
                                                                 body.get('magento_shipment_status'))
                request.env['ir.logging'].sudo().create({
                    'name': 'api-shipment-update-status-magento',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(body) if body else None,
                    'func': 'update_shipment_status',
                    'line': '0',
                })
                return shipment_status_fail
            elif body.get('magento_shipment_status') == 'da_giao_hang':
                shipment_status_fail = self.shipment_status_success(body.get('magento_do_id'),
                                                                    body.get('magento_shipment_status'))
                request.env['ir.logging'].sudo().create({
                    'name': 'api-shipment-update-status-magento',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(body) if body else None,
                    'func': 'update_shipment_status',
                    'line': '0',
                })
                return shipment_status_fail
            else:
                raise ValidationError('This is api update status delivering fail')
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-shipment-update-status-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'update_shipment_status',
                'line': '0',
            })
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/delivery-order/shipping-label', methods=['POST'], auth='public', type='json', csrf=False)
    def update_shipping_label(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            delivery_order_ids = list(map(int, body.keys()))
            delivery_orders = request.env['stock.picking'].browse(delivery_order_ids)
            if delivery_orders.filtered(lambda sp: not sp.sale_id.is_magento_order):
                raise ValidationError('Only allow Magento order to add shipping label via API!')
            if delivery_orders.filtered(lambda sp: sp.sale_id.state not in ('sale', 'done')):
                raise ValidationError('Only allow confirmed sale order to add shipping label via API!')
            for do in delivery_orders:
                do.write(body.get(str(do.id), {}))
                if do.shipping_label and do.location_id:
                    if do.location_id.warehouse_id and do.location_id.warehouse_id.users_receive_noti:
                        user_receive = [user.partner_id.id for user in do.location_id.warehouse_id.users_receive_noti]
                        do.sudo().message_post(
                            body="DO " + do.name + _(' đã có mã vận đơn.'),
                            message_type='notification',
                            partner_ids=user_receive)
            request.env['ir.logging'].sudo().create({
                'name': 'api-delivery-order-shipping-label-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(body) if body else None,
                'func': 'update_shipping_label',
                'line': '0',
            })
            return valid_response(
                head='shipping_label_updated', message=f'Updated delivery orders: {delivery_order_ids}'
            )
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-delivery-order-shipping-label-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'update_shipping_label',
                'line': '0',
            })
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/assign-source', methods=['GET'], auth='public', type='json', csrf=False)
    def assign_source(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            source_location = body.get('source_location')
            if not source_location:
                raise ValidationError('Source location is required!')
            source_location = slugify_one(source_location).replace('-', '_')
            warehouse = request.env['stock.warehouse'].sudo().search([('source_code_name', '=ilike', source_location)])
            if not warehouse:
                raise ValidationError('Source location not found!')
            location_id = warehouse.lot_stock_id
            if not location_id:
                raise ValidationError('Source location not found!')
            # get stock_quant
            query_stock_quant = """select id, product_id, location_id, quantity from stock_quant where location_id = %s"""
            request.env.cr.execute(query_stock_quant, (location_id.id,))
            stock_quant_obj = request.env.cr.dictfetchall()
            # get reservation qty of stock_move
            result = []
            if stock_quant_obj:
                for stock_quant in stock_quant_obj:
                    product_obj = request.env['product.product'].sudo().search(
                        [('id', '=', stock_quant.get('product_id'))])
                    stock_move_obj = request.env['stock.move'].sudo().search(
                        [('product_id', '=', stock_quant.get('product_id')),
                         ('location_id', '=', stock_quant.get('location_id')),
                        ('picking_id.magento_do_id', '=', False),
                         ('picking_id.is_boo_do_return', '=', False)])
                    if stock_move_obj:
                        reservation_qty = sum(stock_move_obj.filtered(lambda sm: sm.state == 'assigned').mapped(
                            's_m2_reserved_quantity'))
                        # reservation_qty < 0: lay so reserved, reservation_qty > 0: khong can lay so reserved
                        if reservation_qty < 0:
                            result.append({
                                'sku': product_obj.default_code,
                                'source': source_location,
                                'quantity': stock_quant.get('quantity'),
                                'reservation_qty': reservation_qty,
                            })
                        else:
                            result.append({
                                'sku': product_obj.default_code,
                                'source': source_location,
                                'quantity': stock_quant.get('quantity'),
                                'reservation_qty': 0,
                            })
                        # disable push reserved len M2
                        stock_move_obj.write({
                            's_disable_push_m2_reserved_quantity': True,
                        })
                    else:
                        result.append({
                            'sku': product_obj.default_code,
                            'source': source_location,
                            'quantity': stock_quant.get('quantity'),
                            'reservation_qty': 0,
                        })
            request.env['ir.logging'].sudo().create({
                'name': 'api-assign-source-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(body) if body else None,
                'func': 'assign_source',
                'line': '0',
            })
            return valid_response(
                head='assign_source_success', message=result
            )
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-assign-source-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'assign_source',
                'line': '0',
            })
            return invalid_response(head='param_input_error', message=e.args)
