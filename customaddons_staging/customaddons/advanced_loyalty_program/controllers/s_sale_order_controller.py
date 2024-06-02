from collections import defaultdict

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.advanced_integrate_magento.controllers.sale_order_controller import AdvancedIntegrateSaleOrderMagento


class CustomSaleOrderMagentoController(AdvancedIntegrateSaleOrderMagento):
    def _grooming_sale_order_data(self, body, order_id=False):
        res = super(CustomSaleOrderMagentoController, self)._grooming_sale_order_data(body, order_id)
        if res.get('order_line'):
            res.pop('order_line')
            order_lines = body.get('order_line', [])
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
                if line['is_line_coupon_program']:
                    product_coupon_program = product_obj.search(
                        [('name', 'ilike', line['product_name']), ('detailed_type', '=', 'service')], limit=1)
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
                    promo_program = request.env['coupon.program'].sudo().search([('ma_ctkm', '=', line['promo_code_line'])], limit=1)
                    if promo_program:
                        coupon_program_id = promo_program.id
                    coupon_coupon = request.env['coupon.coupon'].sudo().search([('boo_code', '=', line['coupon_code_line'])], limit=1)
                    if coupon_coupon and coupon_coupon.program_id:
                        coupon_program_id = coupon_coupon.program_id.id
                elif line.get('is_loyalty_reward_line'):
                    product_loyalty_reward = product_obj.search( [('name', 'ilike', line['product_name']), ('detailed_type', '=', 'service'),
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
                    'is_loyalty_reward_line': line.get('is_loyalty_reward_line', False),
                    's_redeem_amount': line.get('redeem_amount', 0.0),
                })]
            shipping_method_name = body.get('shipping_method', '')
            shipping_method_price = body.get('shipping_method_price', '')
            if shipping_method_name:
                shipping_method = request.env['delivery.carrier'].sudo().search(
                    [('name', 'ilike', shipping_method_name)],
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
                            'product_id': shipping_method_product_new_value.id
                        })
                        res['s_carrier_id'] = shipping_method_new.id
                        if shipping_method_product_new_value.lst_price > 0:
                            res['order_line'] += [(0, 0, {
                                'product_id': shipping_method_product_new_value.id,
                                'is_delivery': True,
                            })]
            return res
