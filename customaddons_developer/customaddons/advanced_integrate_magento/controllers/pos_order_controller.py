# -*- coding: utf-8 -*-
from odoo import http, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.http import request
from ..tools.api_wrapper import validate_integrate_token
from ..tools.common import invalid_response, valid_response
from .sale_order_controller import _get_partner_id
from odoo.http import Response


class AdvancedIntegratePOSOrderMagento(http.Controller):

    @staticmethod
    def _format_order(pos_orders):
        res = []
        for order in pos_orders.sudo():
            res.append({
                'id': order.id,
                'name': order.name,
                'order_code': order.pos_reference.strip(
                    'Đơn hàng') if 'Đơn hàng' in order.pos_reference else order.pos_reference.strip(
                    'Order'),
                'customer': order.partner_id.name_get(),
                'state': order.state,
                'payment_methods': order.payment_ids.read(
                    ['payment_date', 'payment_method_id', 'payment_status', 'amount', 'currency_id']
                ),
                'shipping_method': False,
                'promotions': order.applied_program_ids.read(['name']),
                'loyalty_points': order.loyalty_points,
                'order_line': [{
                    'product': line.product_id.name_get(),
                    'note': line.name,
                    'sku': line.product_id.sku,
                    'm2_url': line.product_id.m2_url,
                    'qty': line.qty,
                    'unit_of_measure': line.product_uom_id.name_get(),
                    'price_unit': line.price_unit,
                    'taxes': line.tax_ids.read(['amount']),
                    'discount': line.discount
                } for line in order.lines]
            })
        return res

    @staticmethod
    def _create_pos_mappings(pos_order_ids):
        order_mappings_obj = request.env['channel.pos.mappings']
        magento_sale_channel = request.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
        if not magento_sale_channel:
            raise ValidationError('Magento2 - Odoo bridge is not defined!')
        if pos_order_ids:
            return order_mappings_obj.with_user(SUPERUSER_ID).create([{
                'channel_id': magento_sale_channel.id,
                'pos_order_id': order.id,
                'ecom_store': 'magento2x',
                'odoo_pos_order_id': order.id,
                'operation': 'export',
                'need_sync': 'no',
            } for order in pos_order_ids])
        return False

    @validate_integrate_token
    @http.route('/pos-order', methods=['GET'], auth='public', type='json', csrf=False)
    def get_pos_orders(self, *args, **kwargs):
        try:
            partner_result = _get_partner_id(kwargs, create=False)
            if not partner_result:
                raise ValidationError('Customer does not exits!')
            elif int(partner_result):
                partner_id = partner_result
            else:
                partner_id = partner_result.get('partner_id')

            partner_obj = request.env['res.partner'].sudo()
            if partner_id:
                partner_obj = partner_obj.browse(partner_id)
            if not partner_obj.exists() or not partner_obj.pos_order_ids:
                return {}
            # self._create_pos_mappings(partner_obj.pos_order_ids)
            limit = int(kwargs.get('limit'))
            page = int(kwargs.get('page'))
            pos_start_index = limit * (page - 1)
            pos_end_index = limit * page
            result_msg = self._format_order(partner_obj.pos_order_ids[pos_start_index:pos_end_index])
            request.env['ir.logging'].sudo().create({
                'name': 'api-pos-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(result_msg) if result_msg else None,
                'func': 'api_call_pos_order_magento',
                'line': '0',
            })
            return result_msg
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-pos-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_call_pos_order_magento',
                'line': '0',
            })
            if e.args == 'Magento2 - Odoo bridge is not defined!':
                return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)
            return invalid_response(head='invalid_query', message=e.args)

    @validate_integrate_token
    @http.route('/pos-order/<string:phone>/<int:order_id>', methods=['GET'], auth='public', type='json', csrf=False)
    def get_pos_order_by_id(self, phone, order_id, *args, **kwargs):
        try:
            if not order_id:
                return invalid_response(head='order_id_missing', message='OrderID Missing!')
            partner_id = request.env['res.partner'].sudo().search([('phone', '=', phone)])
            # pos_order_obj = request.env['pos.order'].sudo()
            order = partner_id.pos_order_ids.browse(order_id)
            if not order.exists():
                return invalid_response(head='order_non_exists', message='Order may not exists or deleted!')
            self._create_pos_mappings(order)
            result_msg = self._format_order(order)
            request.env['ir.logging'].sudo().create({
                'name': 'api-get-pos-order-by-id-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(result_msg) if result_msg else None,
                'func': 'api_call_get_pos_order_by_id_magento',
                'line': '0',
            })
            return result_msg
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-get-pos-order-by-id-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_call_get_pos_order_by_id_magento',
                'line': '0',
            })
            return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)

    @validate_integrate_token
    @http.route('/check_coupon/<coupon_code>', method=['GET'], auth='public', type='json', csrf=False)
    def check_coupon(self, coupon_code, *args, **kwargs):
        try:
            coupon_obj = request.env['coupon.coupon'].sudo().search([('boo_code', '=', coupon_code)])
            if len(coupon_obj) > 0:
                request.env['ir.logging'].sudo().create({
                    'name': 'api-check-coupon-magento',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(coupon_obj) if coupon_obj else None,
                    'func': 'api_call_check_coupon',
                    'line': '0',
                })
                return coupon_obj.read(['state'])
            else:
                raise ValidationError('Mã Coupon không tồn tại !')
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-check-coupon-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_call_check_coupon',
                'line': '0',
            })
            return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)

    # @validate_integrate_token
    # @http.route('/check_gift_card/<gift_card_code>', method=['GET'], auth='public', type='json', csrf=False)
    # def check_gift_card(self, gift_card_code, *args, **kwargs):
    #     try:
    #         giftcard_obj = request.env['gift.card'].sudo().search([('code', '=', gift_card_code)], limit=1)
    #         if len(giftcard_obj) > 0:
    #             request.env['ir.logging'].sudo().create({
    #                 'name': 'api-delivery-order-magento',
    #                 'type': 'server',
    #                 'dbname': 'boo',
    #                 'level': 'INFO',
    #                 'path': 'url',
    #                 'message': str(giftcard_obj) if giftcard_obj else None,
    #                 'func': 'api_call_check_gift_card',
    #                 'line': '0',
    #             })
    #             return giftcard_obj.read(
    #                 ['code', 'expired_date', 'balance', 'state', 'discount_percentage', 'discount_amount'])
    #     except Exception as e:
    #         request.env['ir.logging'].sudo().create({
    #             'name': 'api-delivery-order-magento',
    #             'type': 'server',
    #             'dbname': 'boo',
    #             'level': 'ERROR',
    #             'path': 'url',
    #             'message': str(e),
    #             'func': 'api_call_check_gift_card',
    #             'line': '0',
    #         })
    #         return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)
