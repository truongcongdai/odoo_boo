# -*- coding: utf-8 -*-
from datetime import datetime as dt
import logging
import json
from odoo import http, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.http import request
from ..tools.api_wrapper import validate_integrate_token, _create_log
from ..tools.common import invalid_response
from .delivery_order_controller import _get_src_order
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


def _grooming_partner_data(body, partner_obj):
    birthday = False
    phone = body['phone']
    customer_name = body.get('customer_name', phone)
    if body.get('birthday'):
        birthday = datetime.strptime(body.get('birthday'), "%d/%m/%Y")
    else:
        if partner_obj.birthday:
            birthday = datetime.strptime(str(partner_obj.birthday), "%Y-%m-%d").strftime("%d/%m/%Y")
    destination_location = body.get('destination_location', [])
    email = body.get('email')
    gender = body.get('gender')
    # TH tạo mới khách hàng từ M2 -> set hạng thấp nhất
    update_rank = False
    lowest_rank = request.env['s.customer.rank'].sudo().search([]).sorted(key='total_amount')[0]
    if not partner_obj:
        update_rank = True
    if not destination_location:
        value = {
            'name': customer_name,
            'phone': phone,
            'email': email,
            'gender': gender,
            'pos_create_customer': 'POS ecommerce',
            'birthday': birthday,
        }
        if update_rank and lowest_rank:
            value.update({
                'related_customer_ranked': lowest_rank.id if update_rank else False,
                'customer_ranked': lowest_rank.rank if update_rank else False,
            })
        return value
    # if partner_obj:
    #     customer_rank_was_reset = request.env.ref('advanced_loyalty_program.s_parameter_customer_rank_was_reset')
    #     if customer_rank_was_reset.sudo().value == 'True':
    #         customer_total_period_revenue = partner_obj.total_period_revenue
    #         customer_rank = request.env['s.customer.rank'].sudo().search([('total_amount', '<=', customer_total_period_revenue)]).sorted(key='total_amount')
    #         if customer_rank:
    #             customer_rank = customer_rank[-1]
    #     else:
    #         if body.get('loyalty_points'):
    #             customer_total_loyalty = partner_obj.loyalty_points + float(body.get('loyalty_points'))
    #         else:
    #             customer_total_loyalty = partner_obj.loyalty_points
    #         customer_rank = request.env['s.customer.rank'].sudo().search([('total_amount', '<=', customer_total_loyalty)],
    #                                                                      limit=1)
    # else:
    #     customer_rank = request.env['s.customer.rank'].sudo().search([('total_amount', '<=', 0)], limit=1)
    street = destination_location.get('street')
    if destination_location.get('city_id'):
        state_id = request.env['res.country.address'].search([('code', '=', destination_location.get('city_id'))],
                                                             limit=1).state_id.id
    else:
        state_id = request.env['res.country.address'].search([('code', '=', destination_location.get('state_id'))],
                                                             limit=1).state_id.id
    district_id = request.env['res.country.address'].search([('code', '=', destination_location.get('district_id'))],
                                                            limit=1)
    ward_id = request.env['res.country.address'].search([('code', '=', destination_location.get('ward_id'))],
                                                        limit=1).id
    country_id = request.env['res.country'].search([('code', '=', destination_location.get('country_id'))], limit=1).id
    if destination_location.get('post_code'):
        zip = destination_location.get('post_code')
    else:
        if partner_obj:
            zip = partner_obj.zip
        else:
            zip = None
    delivery_phone = destination_location.get('delivery_phone')
    delivery_name = destination_location.get('delivery_name')
    if delivery_name and len(delivery_name) > 30:
        raise ValidationError('Trường tên khách hàng chỉ được phép nhập tối đa 30 ký tự (tính cả khoảng trắng).'
                              '\nSố ký tự tên khách hàng này đang có: %s ' % len(
            delivery_name) + '\nVui lòng nhập lại.')
    vals = {
        'name': customer_name,
        'phone': phone,
        'email': email,
        'gender': gender,
        'pos_create_customer': 'POS ecommerce',
        'birthday': birthday,
        'street': street,
        'state_id': state_id,
        'district_id': district_id.id,
        'district': district_id.name_with_type,
        'ward_id': ward_id,
        'country_id': country_id,
        'zip': zip,
        'delivery_phone': delivery_phone,
        'delivery_name': delivery_name
    }
    if update_rank and lowest_rank:
        vals.update({
            'related_customer_ranked': lowest_rank.id if update_rank else False,
            'customer_ranked': lowest_rank.rank if update_rank else False,
        })
    return vals


def _get_partner_id(body, create=True, api_customer=False):
    if not isinstance(body, dict):
        raise ValidationError('body format wrong!')
    if 'phone' not in body.keys():
        raise ValidationError('Missing required parameter `phone`!')
    partner_obj = request.env['res.partner'].sudo().search([('phone', '=', body.get('phone'))], order='id asc', limit=1)
    if not create:
        return partner_obj and partner_obj.id or False
    if partner_obj:
        create_params = _grooming_partner_data(body, partner_obj)
        partner_address_ship = {
            'type': 'delivery',
            'street': create_params.get('street') if create_params.get('street') else '',
            'phone_delivery': create_params.get('delivery_phone'),
            'parent_id': partner_obj.id,
            'ward_id': create_params.get('ward_id') if create_params.get('ward_id') else False,
            'district_id': create_params.get('district_id') if create_params.get('district_id') else False,
            'state_id': create_params.get('state_id') if create_params.get('state_id') else False,
            'name': create_params.get('delivery_name'),
        }
        responsive = dict()
        partner_address_delivery = request.env['res.partner'].sudo().search(
            [('parent_id', '=', partner_obj.id), ('type', '=', 'delivery')])
        if not api_customer:
            if partner_address_delivery:
                list_ward_id = []
                for address_delivery in partner_address_delivery:
                    if address_delivery.ward_id:
                        list_ward_id.append(address_delivery.street + str(address_delivery.ward_id.id))
                if (create_params.get('street') + str(create_params.get('ward_id'))) not in list_ward_id:
                    partner_shipping_id = request.env['res.partner'].sudo().create(partner_address_ship)
                    responsive['partner_shipping'] = partner_shipping_id.id
                    # if address_delivery.ward_id:
                    #     list_ward_id.append(address_delivery.ward_id.id)
                    # if create_params.get('ward_id') != address_delivery.ward_id.id and create_params.get('street') != address_delivery.street:
                    #     partner_shipping_id = request.env['res.partner'].sudo().create(partner_address_ship)
                    #     responsive['partner_shipping'] = partner_shipping_id.id
            else:
                partner_shipping_id = request.env['res.partner'].sudo().create(partner_address_ship)
                responsive['partner_shipping'] = partner_shipping_id.id
        if 'delivery_phone' in create_params.keys():
            create_params.pop('delivery_phone')
        if 'delivery_name' in create_params.keys():
            create_params.pop('delivery_name')
        if body.get('destination_location', []):
            destination_location = body.get('destination_location', [])
            if not destination_location.get('is_changed'):
                keys_to_delete = ["street", "state_id", "district_id", "district", "ward_id", "country_id", "zip"]
                for key in keys_to_delete:
                    create_params.pop(key, None)
        if api_customer:
            partner_obj.with_context(is_call_api=True).write(create_params)
        responsive['partner_id'] = partner_obj.id
        return responsive
    try:
        create_params = _grooming_partner_data(body, partner_obj)
        if 'delivery_phone' in create_params.keys():
            create_params.pop('delivery_phone')
        if 'delivery_name' in create_params.keys():
            create_params.pop('delivery_name')
        create_partner_obj = request.env['res.partner'].with_user(SUPERUSER_ID).create(create_params)
        responsive = dict()
        responsive['partner_id'] = create_partner_obj.id
        return responsive
    except Exception as e:
        _logger.error('Can not create customer from params %s' % create_params)
        raise ValidationError(e.args)


class AdvancedIntegrateSaleOrderMagento(http.Controller):

    @staticmethod
    def _create_sale_order_mappings(orders, action, default_key=None, default_value=None):
        assert bool(default_key) == bool(default_value)
        assert action in ('import', 'export')
        order_mappings_obj = request.env['channel.order.mappings']
        magento_sale_channel = request.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
        if not magento_sale_channel:
            raise ValidationError('Magento2 - Odoo bridge is not defined!')
        if orders:
            create_data = []
            for order in orders:
                data = {
                    'channel_id': magento_sale_channel.id,
                    'order_name': order.id,
                    'ecom_store': 'magento2x',
                    'odoo_order_id': order.id,
                    'operation': action,
                    'need_sync': 'no',
                }
                if default_key and default_value:
                    data.update({default_key: default_value})
                create_data.append(data)
            return order_mappings_obj.with_user(SUPERUSER_ID).create(create_data)
        return False

    @staticmethod
    def _format_order_data(orders):
        res = []
        for order in orders.sudo():
            res.append({
                'id': order.id,
                'm2_so_id': order.m2_so_id,
                'name': order.name,
                'customer': order.partner_id.name_get(),
                'state': order.state,
                'shipping_method': order.carrier_id.name_get(),
                'payment_method': order.payment_method,
                'promotions': order.applied_program_ids.read(['name']),
                'promo_code': order.promo_code,
                'loyalty_points': order.loyalty_points,
                'loyalty_used_m2': order.loyalty_used_m2,
                'gift_card_code': order.gift_card_code,
                'gift_card_discount_amount': order.gift_card_discount_amount,
                'order_line': [{
                    'product': line.product_id.name_get(),
                    'note': line.name,
                    'sku': line.product_id.sku,
                    'm2_url': line.m2_url,
                    'qty': line.product_uom_qty,
                    'unit_of_measure': line.product_uom.name_get(),
                    'price_unit': line.price_unit,
                    'taxes': line.tax_id.read(['amount']),
                    'm2_total_line_discount': line.discount,
                    'pod_image_url': line.pod_image_url
                } for line in order.order_line]
            })
        return res

    @staticmethod
    def _grooming_sale_order_data(body, order_id=False):
        res = dict()
        if not isinstance(body, dict):
            raise ValidationError('Post data should be a json object!')
        if 'id' not in body.keys():
            raise ValidationError('Magento Order ID not set!')
        if body.get('customer_pickup_date'):
            customer_pickup_date = datetime.strptime(body.get('customer_pickup_date'), "%Y-%m-%d %H:%M") if body.get(
                'customer_pickup_date') else False
            res['customer_pickup_date'] = customer_pickup_date - timedelta(hours=7)
        if body.get('completed_date'):
            completed_date = datetime.strptime(body.get('completed_date'), "%Y-%m-%d %H:%M:%S") if body.get(
                'completed_date') else False
            res['completed_date'] = completed_date - timedelta(hours=7)
        # if body.get('shipment_status_date'):
        #     shipment_status_date = datetime.strptime(body.get('shipment_status_date'), "%Y-%m-%d %H:%M:%S") if body.get(
        #         'shipment_status_date') else False
        #     res['shipment_status_date'] = shipment_status_date - timedelta(hours=7)
        # partner_result = _get_partner_id(body)
        # res['partner_id'] = partner_result['partner_id']
        # if partner_result.get('partner_shipping'):
        #     res['partner_shipping_id'] = partner_result['partner_shipping']
        sale_order_id = request.env['sale.order'].sudo().search([('id', '=', order_id)])
        if not sale_order_id or (
                sale_order_id and not sale_order_id.s_facebook_sender_id and not sale_order_id.s_zalo_sender_id):
            partner_result = _get_partner_id(body)
            res['partner_id'] = partner_result['partner_id']
            if partner_result.get('partner_shipping'):
                res['partner_shipping_id'] = partner_result['partner_shipping']
        order_lines = body.get('order_line', [])
        res['is_magento_order'] = True
        # res['online_order_id'] = body['id']
        res['coupon_code'] = body.get('coupon_code', '')
        res['promo_code'] = body.get('coupon_code', '')
        res['s_promo_code'] = body.get('promo_code', '')
        res['loyalty_points'] = body.get('loyalty_points', 0)
        res['loyalty_used_m2'] = body.get('loyalty_used_m2', 0)
        res['gift_card_code'] = body.get('gift_card_code', '')
        res['gift_card_discount_amount'] = body.get('gift_card_discount_amount', '')
        res['payment_method'] = body.get('payment_method', 'cod').lower()
        res['m2_so_id'] = body.get('m2_so_id', '')
        res['source_id'] = request.env.ref('advanced_sale.utm_source_magento_order').id
        # sale_order_id = request.env['sale.order'].sudo().search([('m2_so_id', '=', body.get('m2_so_id'))])
        if body.get('sale_order_status') == 'moi':
            res['sale_order_status'] = 'moi'
        elif body.get('sale_order_status') == 'dang_xu_ly':
            res['sale_order_status'] = 'dang_xu_ly'
        elif body.get('sale_order_status') == 'dang_giao_hang':
            res['sale_order_status'] = 'dang_giao_hang'
        elif body.get('sale_order_status') == 'dang_chuyen_hoan':
            res['sale_order_status'] = 'dang_chuyen_hoan'
        elif body.get('sale_order_status') == 'don_hoan_1_phan':
            do_m2_done = sale_order_id.picking_ids.filtered(lambda p: p.magento_do_id and p.state == 'done')
            if do_m2_done:
                shipment_status_do_m2_done = do_m2_done.mapped('shipment_status')
                if sale_order_id.sale_order_status == 'dang_giao_hang' or sale_order_id.sale_order_status == 'dang_xu_ly' or sale_order_id.sale_order_status == 'giao_hang_that_bai' and (
                        False in shipment_status_do_m2_done or 'giao_hang_thanh_cong' in shipment_status_do_m2_done):
                    res['sale_order_status'] = 'dang_giao_hang'
                else:
                    res['sale_order_status'] = 'giao_hang_that_bai'
        elif body.get('sale_order_status') == 'don_hoan':
            res['sale_order_status'] = 'giao_hang_that_bai'
        elif body.get('sale_order_status') == 'hoan_thanh_1_phan':
            res['sale_order_status'] = 'hoan_thanh_1_phan'
        elif body.get('sale_order_status') == 'hoan_thanh':
            res['sale_order_status'] = 'hoan_thanh'
        elif body.get('sale_order_status') == 'huy_bo':
            res['sale_order_status'] = 'huy'
        elif body.get('sale_order_status') == 'closed':
            res['sale_order_status'] = 'closed'
        if not order_lines:
            return res
        res['order_line'] = [(5, 0, 0)]
        product_obj = request.env['product.product'].sudo()
        for line in order_lines:
            if 'm2_url' not in line.keys():
                raise ValidationError('Magento Order line must have Magento link to product!')
            if 'product' not in line.keys():
                raise ValidationError('Magento Order line must have product!')
            if 'qty' not in line.keys() or line['qty'] < 0:
                raise ValidationError('Magento Order line must have positive quantity!')
            if 'price_unit' not in line.keys() or line['price_unit'] < 0:
                raise ValidationError('Magento Order line must have positive price!')
            if line.get('taxes', []):
                sale_taxes = request.env['account.tax'].sudo().search(
                    [('type_tax_use', '=', 'sale'), ('amount', 'in', line['taxes'])]
                )
            coupon_program_id = False
            if line.get('is_line_coupon_program'):
                product_coupon_program = product_obj.search([('name', 'ilike', line['product_name']),('detailed_type','=','service')], limit=1)
                if product_coupon_program:
                    product_coupon_program.sudo().write({
                        'lst_price': -line['price_unit']
                    })
                    product = product_coupon_program
                else:
                    product = product_obj.create({
                        'name': line['product_name'],
                        'detailed_type': 'service',
                        'lst_price': -float(line['price_unit']) if line['price_unit'] else 0,
                        'is_line_ctkm_m2': True
                    })
                promo_program = request.env['coupon.program'].sudo().search([('ma_ctkm', '=', line['promo_code_line'])],
                                                                            limit=1)
                if promo_program:
                    coupon_program_id = promo_program.id
                coupon_coupon = request.env['coupon.coupon'].sudo().search(
                    [('boo_code', '=', line['coupon_code_line'])],
                    limit=1)
                if coupon_coupon and coupon_coupon.program_id:
                    coupon_program_id = coupon_coupon.program_id.id
            elif line.get('is_loyalty_reward_line'):
                product_loyalty_reward = product_obj.search(
                    [('name', 'ilike', line['product_name']), ('detailed_type', '=', 'service'),
                     ('s_loyalty_product_reward', '=', True)], limit=1)
                if product_loyalty_reward:
                    product_loyalty_reward.sudo().write({
                        'lst_price': -line['price_unit']
                    })
                    product = product_loyalty_reward
                else:
                    product = product_obj.create({
                        'name': line['product_name'],
                        'detailed_type': 'service',
                        'lst_price': -float(line['price_unit']) if line['price_unit'] else 0,
                        's_loyalty_product_reward': True
                    })
            else:
                product = product_obj.browse(line['product'])
            if not product.exists():
                raise ValidationError('Product does not exits!')
            res['order_line'] += [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'm2_url': line['m2_url'],
                'product_uom_qty': line['qty'],
                'product_uom': product.uom_id.id,
                'price_unit': line['price_unit'] if product.detailed_type == 'product' else product.lst_price,
                'tax_id': [(6, 0, sale_taxes.ids)],
                'm2_total_line_discount': line.get('m2_total_line_discount', 0.0),
                'promo_code_line': line['promo_code_line'],
                'coupon_code_line': line['coupon_code_line'],
                'is_line_coupon_program': line['is_line_coupon_program'],
                'coupon_program_id': coupon_program_id,
                'is_product_free': line.get('is_product_free', False),
                'is_product_reward': False,
                'pod_image_url': line.get('pod_image_url', False),
                'is_loyalty_reward_line': line.get('is_loyalty_reward_line', False)
            })]
        shipping_method_name = body.get('shipping_method', '')
        shipping_method_price = body.get('shipping_method_price', '')
        if shipping_method_name:
            shipping_method = request.env['delivery.carrier'].sudo().search([('name', 'ilike', shipping_method_name)],
                                                                            limit=1)
            if shipping_method:
                res['s_carrier_id'] = shipping_method.id
                shipping_method_product_old_value = request.env['product.product'].sudo().search([
                    ('id', '=', shipping_method.product_id.id)
                ])
                shipping_method_product_old_value.write({
                    'lst_price': float(shipping_method_price) if shipping_method_price else 0,
                    'la_phi_ship_hang_m2': True
                })
                if not shipping_method.product_id:
                    raise ValidationError('Product service does not exits!')
                if float(shipping_method_price) > 0:
                    res['order_line'] += [(0, 0, {
                        'product_id': shipping_method.product_id.id,
                        'price_unit': float(shipping_method_price),
                        'is_delivery': True,
                    })]
            else:
                shipping_method_product_new_value = request.env['product.product'].sudo().create({
                    'name': shipping_method_name,
                    'detailed_type': 'service',
                    'lst_price': float(shipping_method_price) if shipping_method_price else 0,
                    'la_phi_ship_hang_m2': True
                })
                if shipping_method_product_new_value:
                    shipping_method_new = request.env['delivery.carrier'].sudo().create({
                        'name': shipping_method_name,
                        'delivery_type': 'fixed',
                        # 'invoice_policy': 'real',
                        'product_id': shipping_method_product_new_value.id
                    })
                    res['s_carrier_id'] = shipping_method_new.id
                    if shipping_method_product_new_value.lst_price > 0:
                        res['order_line'] += [(0, 0, {
                            'product_id': shipping_method_product_new_value.id,
                            'is_delivery': True,
                        })]
        return res

    def _get_sale_orders(self, **kwargs):
        partner_result = _get_partner_id(kwargs, create=False)
        partner_id = partner_result['partner_id']
        partner_obj = request.env['res.partner'].with_user(SUPERUSER_ID)
        if partner_id:
            partner_obj = partner_obj.browse(partner_id)
        if not partner_obj.exists() or not partner_obj.sale_order_ids:
            return {}
        self._create_sale_order_mappings(partner_obj.sale_order_ids, action='export')
        return self._format_order_data(partner_obj.sale_order_ids)

    def _check_gift_card(self, created_order):
        if created_order.gift_card_code:
            gift_card = request.env['gift.card'].sudo().search(
                [('code', '=', created_order.gift_card_code), ('state', '=', 'valid')], limit=1)
            product_gift_card = request.env['product.product'].sudo().search(
                [('is_gift_card', '=', True), ('detailed_type', '=', 'service')], limit=1)
            if not product_gift_card:
                product_gift_card = request.env['product.product'].sudo().create({
                    'name': 'Gift Card',
                    'detailed_type': 'service',
                    'is_gift_card': True,
                    'sync_push_magento': False,
                    'purchase_ok': False,
                    'default_code': 'gift_card',
                    'ma_vat_tu': 'gift_card_code',
                })
            if gift_card and gift_card.balance > 0:
                vals = {
                    'name': created_order.name,
                    'order_id': created_order.id,
                    'product_id': product_gift_card.id,
                    'price_unit': float(-created_order.gift_card_discount_amount)
                }
                gift_card.redeem_line_ids = [(0, 0, vals)]
                gift_card.write({
                    'balance': gift_card.balance - float(created_order.gift_card_discount_amount)
                })

    def _create_sale_order(self):
        sale_order_obj = request.env['sale.order']
        body = self._grooming_sale_order_data(request.jsonrequest)
        created_order = sale_order_obj.with_user(SUPERUSER_ID).create(body)
        if created_order.gift_card_code:
            self._check_gift_card(created_order)
        created_order.action_confirm()
        if created_order.state == 'sale':
            # them ma coupon
            if created_order.coupon_code:
                coupon_m2_ids = created_order.coupon_code.split(',')
                for coupon_m2_id in coupon_m2_ids:
                    coupon_odoo = request.env['coupon.coupon'].search(
                        [('boo_code', '=', coupon_m2_id), ('state', '!=', 'used')], limit=1)
                    if coupon_odoo:
                        coupon_odoo.write({
                            'state': 'used',
                            'sales_order_id': created_order.id,
                        })
                        coupon_odoo.state = 'used'
            # them ctkm
            if created_order.promo_code:
                promo_id = request.env['coupon.program'].sudo().search(
                    [('promo_code_usage', '=', 'code_needed'), ('promo_code', '=', created_order.promo_code)], limit=1)
                if promo_id:
                    created_order.no_code_promo_program_ids = [(4, promo_id.id)]
            if created_order.s_promo_code:
                list_promo_code = created_order.s_promo_code.split(',')
                promo_ids = request.env['coupon.program'].sudo().search(
                    [('promo_code_usage', '=', 'code_needed'), ('ma_ctkm', 'in', list_promo_code)])
                if len(promo_ids) > 0:
                    created_order.no_code_promo_program_ids = [(4, promo.id) for promo in promo_ids]

        # if created_order.gift_card_code:
        #     self._check_gift_card(created_order)
        self._create_sale_order_mappings(
            created_order, action='import', default_key='store_order_id', default_value=request.jsonrequest['id']
        )
        # self.send_mail_customer(created_order)
        return self._format_order_data(created_order)

    def _get_sale_order_by_id(self, order_id):
        order = request.env['sale.order'].with_user(SUPERUSER_ID).browse(order_id)
        if not order.exists():
            raise ValidationError('Order may not exists or deleted!')
        self._create_sale_order_mappings(order, action='export')
        return self._format_order_data(order)

    def _edit_sale_order_by_id(self, order_id):
        order = request.env['sale.order'].with_user(SUPERUSER_ID).browse(order_id)
        if not order.exists():
            raise ValidationError('Order may not exists or deleted!')
        body = request.jsonrequest
        if not order.is_magento_order:
            raise ValidationError('Magento should not edit non-magento sale order!')
        # cap nhat state khi M2 huy SO
        if order.sale_order_status not in ['hoan_thanh', 'huy','hoan_thanh_1_phan']:
            if 'canceled' in [body.get('m2_state'), body.get('m2_status')]:
                # sale_order_cancel = request.env['sale.order.cancel'].sudo().create({
                #     'order_id': order.id
                # })
                picking_done = order.picking_ids.filtered(
                    lambda picking: picking.state in ['done'] and picking.transfer_type == 'out')
                if not picking_done:
                    order.with_context(api_cancel_do=True)._action_cancel()
                    # if not picking_done:
                order.sudo().write({
                    'sale_order_status': 'huy',
                    'completed_date': datetime.strptime(body.get('completed_date'), "%Y-%m-%d %H:%M:%S") -
                                      timedelta(hours=7) if body.get('completed_date') else False
                })
                if len(picking_done):
                    for picking_id in picking_done:
                        return_picking_old_id = order.picking_ids.filtered(lambda p: picking_id.name in p.origin)
                        if return_picking_old_id:
                            break
                        # Tao lenh return DO
                        return_picking_id = request.env['stock.return.picking'].create({'picking_id': picking_id.id})
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
                # else:
                #     raise ValidationError('Đơn hàng đã có DO ở trạng thái sẵn sàng')
            else:
                order_data = self._grooming_sale_order_data(body, order_id)
                if 'order_line' in order_data.keys():
                    order_data.pop('order_line')
                if order_data.get('completed_date'):
                    completed_date = order_data.get('completed_date')
                    order_data.update({
                        'completed_date': completed_date.strftime("%Y-%m-%d %H:%M:%S") if completed_date else None
                    })
                request.env.cr.execute("""INSERT INTO s_magento_order_queue (s_m2_order_data, s_odoo_order_id) VALUES ('{order_data}', '{order_id}'); """.format(order_data=json.dumps(order_data,default=str), order_id=order.id))
                if order.state == 'draft':
                    order.sudo().write({
                        'state': 'sale'
                    })
            source_id = request.env.ref('advanced_sale.utm_source_magento_order')
            if source_id and not order.s_facebook_sender_id and not order.s_zalo_sender_id:
                order.sudo().write({
                    'source_id': source_id.id
                })
            self._create_sale_order_mappings(
                order, action='import', default_key='store_order_id', default_value=request.jsonrequest['id']
            )
            return self._format_order_data(order)
        else:
            return False

    @validate_integrate_token
    @http.route(['/sale-order'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def api_call_sale_orders(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            if request.httprequest.method == 'GET':
                return self._get_sale_orders(kwargs)
            sale_order_id = request.env['sale.order'].search([('m2_so_id', '=', body.get('m2_so_id'))], limit=1)
            if sale_order_id:
                request.env['ir.logging'].sudo().create({
                    'name': 'api-create-sale-order-magento',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': 'SO duplicate:' + str(sale_order_id.read(['name', 'm2_so_id'])[0]),
                    'func': 'api_call_sale_orders',
                    'line': '0',
                })
                sale_order_created = self._format_order_data(sale_order_id)
                return sale_order_created
            create_sale_order = self._create_sale_order()
            request.env['ir.logging'].sudo().create({
                'name': 'api-create-sale-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': 'body: ' + str(body) + 'response: ' + str(create_sale_order) if body else None,
                'func': 'api_call_sale_orders',
                'line': '0',
            })
            return create_sale_order
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-create-sale-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'api_call_sale_orders',
                'line': '0',
            })
            if e.args == 'Magento2 - Odoo bridge is not defined!':
                return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)
            return invalid_response(head='provided_data_failures', message=e.args)

    @validate_integrate_token
    @http.route('/sale-order/<int:order_id>', methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def api_call_sale_order_by_id(self, order_id=None, *args, **kwargs):
        try:
            body = request.jsonrequest
            if request.httprequest.method == 'GET':
                return self._get_sale_order_by_id(order_id)
            edit_sale_order_by_id = self._edit_sale_order_by_id(order_id)
            if edit_sale_order_by_id:
                request.env['ir.logging'].sudo().create({
                    'name': 'api-update-sale-order-magento',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(body) if body else None,
                    'func': 'api_call_sale_order_by_id',
                    'line': '0',
                })
                return edit_sale_order_by_id
            else:
                return False
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-update-sale-order-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'api_call_sale_order_by_id',
                'line': '0',
            })
            if e.args == 'Magento2 - Odoo bridge is not defined!':
                return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)
            return invalid_response(head='provided_data_failures', message=e.args)

    @validate_integrate_token
    @http.route('/gift-card/<gift_card_code>', method=['GET'], auth='public', type='json', csrf=False)
    def get_gift_card(self, gift_card_code, *args, **kwargs):
        try:
            gift_card_obj = request.env['gift.card'].sudo().search([('code', '=', gift_card_code)])
            if len(gift_card_obj):
                msg_result = gift_card_obj.read()
                partner_phone = False
                if gift_card_obj.partner_id:
                    partner_phone = gift_card_obj.partner_id.phone
                msg_result[0]['phone'] = partner_phone
                return msg_result
        except Exception as e:
            return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)

    @staticmethod
    def _format_order_invoices_data(order):
        res = []
        for inv in order.invoice_ids:
            res.append({
                'odoo_invoice_id': inv.id,
                'customer': inv.partner_id.name_get(),
                'invoice_line': [{
                    'product': line.product_id.name_get(),
                    'sku': line.product_id and line.product_id.sku or '',
                    'quantity': line.quantity,
                    'taxes': line.tax_ids.read(['amount']),
                    'price': line.price_unit
                } for line in inv.invoice_line_ids]
            })
        return res

    @validate_integrate_token
    @http.route('/sale-order/create-invoices', method=['POST'], auth='public', type='json', csrf=False)
    def create_order_invoices(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            order, kwargs = _get_src_order(body)
            if not order.is_magento_order:
                raise ValidationError('M2 should not create invoice for Sale Order not created from M2!')
            payment_method = body.get('payment_method')
            if not isinstance(payment_method, str):
                raise ValidationError('Only support 2 payment methods: `cod` and `online`')
            payment_method = payment_method.lower()
            if order.payment_method != payment_method:
                if order.state in ('sale', 'done'):
                    raise ValidationError('Confirmed Sale Order can not change its payment method!')
                order.with_user(SUPERUSER_ID).write({'payment_method': payment_method})
            order.with_user(SUPERUSER_ID).create_invoices_via_api_calling(body)
            format_order_invoices_data = self._format_order_invoices_data(order)
            request.env['ir.logging'].sudo().create({
                'name': 'api-sale-order-create-invoices-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(body) if body else None,
                'func': 'create_order_invoices',
                'line': '0',
            })
            return format_order_invoices_data
        except Exception as e:
            # body.update({'order': order.name})
            # _create_log(
            #     name='fail_action_create_invoices_for_order',
            #     message=f'body={body}\nerror={e.args}',
            #     func='create_order_invoices'
            # )
            request.env['ir.logging'].sudo().create({
                'name': 'api-sale-order-create-invoices-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'create_order_invoices',
                'line': '0',
            })
            return invalid_response(head='fail_action_create_invoices_for_order', message=e.args)

    # @validate_integrate_token
    # @http.route('/sale-order/update-status-invoices', method=['POST'], auth='public', type='json', csrf=False)
    # def update_status_invoices(self, *args, **kwargs):
    #     try:
    #         body = request.jsonrequest
    #         if body.get('payment_method') == 'cod':
    #             invoice_id = request.env['account.move'].sudo().search(
    #                 [('magento_do_id', '=', body.get('magento_do_id'))], limit=1)
    #             if invoice_id:
    #                 if invoice_id.state == 'posted':
    #                     invoice_id.button_draft()
    #                 if invoice_id.state == 'draft':
    #                     invoice_id.button_cancel()
    #                 return invoice_id.read(['state'])
    #         else:
    #             raise ValidationError('Payment method must be COD')
    #     except Exception as e:
    #         return invalid_response(head='fail_action_update_invoices_for_order', message=e.args)

    # region TODO @theanh: send e-mail to customer from Odoo
    # def send_mail_customer(self, order):
    #     if not order:
    #         raise ValidationError('order does not exits')
    #     order_name = 'Đơn hàng ' + order['name']
    #     template_id = order._find_mail_template()
    #     body = 'Bạn đã đặt hàng thành công! Giá trị ' + order_name + ' là ' + str(order.amount_total)
    #     if not template_id:
    #         template_id = False
    #     template = request.env['mail.template'].sudo().browse(template_id)
    #     if template.lang:
    #         lang = template._render_lang(order.ids)[order.id]
    #     partner_ids = order.partner_id.ids
    #     if not partner_ids:
    #         raise ValidationError('partner_ids does not exits')
    #     email_from = request.env.company.email
    #     ctx = {
    #         'default_model': 'sale.order',
    #         'default_res_id': order.id,
    #         'default_use_template': bool(template_id),
    #         'default_template_id': template_id,
    #         'default_composition_mode': 'comment',
    #         'custom_layout': "mail.mail_notification_paynow",
    #         'mark_so_as_sent': True,
    #         'force_email': True,
    #         'model_description': order.with_context(lang=lang)._description,
    #     }
    # attachment when send email
    # report_template_id = request.env.ref('sale.action_report_saleorder').sudo()._render_qweb_pdf([order.id])
    # data_record = base64.b64encode(report_template_id[0])
    # ir_values = {
    #     'name': "Customer Report",
    #     'type': 'binary',
    #     'datas': data_record,
    #     'store_fname': data_record,
    #     'mimetype': 'application/x-pdf',
    # }
    # order_pdf_attachment = request.env['ir.attachment'].sudo().create(ir_values)
    # attachment when send email
    # order_mail_composer = request.env['mail.compose.message'].sudo().with_context(ctx).create({
    #     'partner_ids': partner_ids,
    #     'subject': order_name,
    #     'template_id': template_id,
    #     'author_id': SUPERUSER_ID,
    #     'email_from': email_from,
    #     'body': body,
    #     # 'attachment_ids': [(6, 0, order_pdf_attachment.ids)],
    # })
    # order_mail_composer.action_send_mail()

    # Tinh toan diem thuong khi gioi thieu link cho ban be, danh gia san pham, dang ky nhan ban tin, sinh nhat, khach hang
    # hoat dong lai sau X ngay
    # endregion
    # @validate_integrate_token
    # @http.route(['/customer-create'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    # def create_res_partner(self, *args, **kwargs):
    #     try:
    #         body = request.jsonrequest
    #         customer_id = _get_partner_id(body)
    #         if not customer_id:
    #             raise ValidationError('Customer may not exists or deleted!')
    #         customer = request.env['res.partner'].sudo().browse(customer_id)
    #         return customer.read(
    #             ['name', 'phone', 'pos_create_customer', 'birthday', 'street', 'city_id', 'district_id', 'ward_id'])
    #     except Exception as e:
    #         return invalid_response(head='create_customer_data_failures', message=e.args)
    #
    # @validate_integrate_token
    # @http.route(['/customer-update'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    # def update_res_partner(self, *args, **kwargs):
    #     try:
    #         body = request.jsonrequest
    #         customer_id = _get_partner_id(body)
    #         if not customer_id:
    #             raise ValidationError('Customer may not exists or deleted!')
    #         customer = request.env['res.partner'].sudo().browse(customer_id)
    #         return customer.read(
    #             ['name', 'phone', 'pos_create_customer', 'birthday', 'street', 'city_id', 'district_id', 'ward_id'])
    #     except Exception as e:
    #         return invalid_response(head='update_customer_data_failures', message=e.args)

    @validate_integrate_token
    @http.route(['/customer-reward-points'], methods=['POST'], auth='public', type='json', csrf=False)
    def edit_customer_reward_points(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            customer_result = _get_partner_id(body, create=False)
            customer_id = customer_result['partner_id']
            if not customer_id:
                raise ValidationError('Customer may not exists or deleted!')
            customer = request.env['res.partner'].sudo().browse(customer_id)
            loyalty_points_value = customer.loyalty_points + body['commercial_points']
            customer.write({
                'loyalty_points': loyalty_points_value,
                'history_points_ids': [(0, 0, {
                    'diem_cong': body.get('commercial_points'),
                    'ly_do': body.get('commercial_points_comment')
                })]
            })
            request.env['ir.logging'].sudo().create({
                'name': 'api-customer-reward-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(body) if body else None,
                'func': 'edit_customer_reward_points',
                'line': '0',
            })
            return customer.read(['name', 'phone', 'loyalty_points'])
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-customer-reward-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'edit_customer_reward_points',
                'line': '0',
            })
            return invalid_response(head='provided_data_failures', message=e.args)
