from odoo import models, fields, api, _
import re
from odoo.exceptions import ValidationError, _logger

import datetime, time
from datetime import timedelta, datetime
from ..tools.api_wrapper_shopee import validate_integrate_token


class SSaleOrder(models.Model):
    _inherit = 'sale.order'

    s_shopee_id_order = fields.Char("ID đơn hàng Shopee", readonly=True)
    s_shopee_is_order = fields.Boolean("Là Đơn Hàng Shopee", readonly=True)
    marketplace_shopee_order_status = fields.Selection([("UNPAID", "UNPAID"),
                                                        ("READY_TO_SHIP", "READY_TO_SHIP"),
                                                        ("PROCESSED", "PROCESSED"),
                                                        ("RETRY_SHIP", "RETRY_SHIP"),
                                                        ("SHIPPED", "SHIPPED"),
                                                        ("TO_CONFIRM_RECEIVE", "TO_CONFIRM_RECEIVE"),
                                                        ("IN_CANCEL", "IN_CANCEL"),
                                                        ("CANCELLED", "CANCELLED"),
                                                        ("TO_RETURN", "TO_RETURN"),
                                                        ("COMPLETED", "COMPLETED")],
                                                       string="Tình trạng đơn hàng Shopee",
                                                       default=False)
    s_shopee_payment_method = fields.Selection([('COD', 'COD'), ('Credit/Debit_Card', 'Credit/Debit Card')])
    s_shopee_return_sn = fields.Char("ID trả hàng Shopee")
    is_return_order_shopee = fields.Boolean(string="Là đơn đổi trả Shopee")
    s_shopee_status_return = fields.Selection(
        [("PROCESSING", "Đang xử lý"), ("CLOSED", "Trả hàng bị từ chối"), ("CANCELLED", "Trả hàng thất bại"),
         ("REFUND_PAID", "Trả hàng thành công"), ("ACCEPTED", "Đồng ý trả hàng")], string="Trạng thái trả hàng Shopee")
    refund_total_shopee = fields.Float()
    s_shopee_time_return = fields.Char("Thời gian trả hàng(timestamp)")

    def _compute_date_order_so_return_shopee(self):
        for rec in self:
            return_detail = self.env['sale.order'].sudo()._get_detail_so_return_shopee(rec.s_shopee_return_sn)
            if return_detail is not None:
                rec.sudo().write({
                    'date_order': datetime.fromtimestamp(int(return_detail.get('create_time')))
                })

    def _check_order_line(self):
        for rec in self:
            if not rec.is_return_order_shopee:
                line_payment = self.env['sale.order'].sudo().get_escrow_detail(rec.s_shopee_id_order)
                line_payment_json = line_payment.json()
                if line_payment.status_code == 200:
                    if line_payment_json.get('response'):
                        res = line_payment_json.get('response')
                        if res.get('order_income'):
                            order_income = res.get('order_income')
                            total_original_price = 0
                            check_order_line = []
                            total_discounted_price = 0
                            if order_income.get('items'):
                                for item in order_income.get('items'):
                                    vals = {}
                                    total_original_price += item.get('original_price')
                                    total_discounted_price += item.get('discounted_price')
                                    if ',' in item.get('model_sku'):
                                        order_line = int(sum(rec.order_line.filtered(
                                            lambda l: l.product_id and l.product_id.marketplace_sku == item.get(
                                                'model_sku')).mapped(
                                            'price_total')))
                                    else:
                                        order_line = int(sum(rec.order_line.filtered(
                                            lambda l: l.product_id and l.product_id.default_code == item.get(
                                                'model_sku')).mapped(
                                            'price_total')))
                                    discounted_price = item.get('discounted_price')
                                    if discounted_price != order_line:
                                        vals = {
                                            'shopee_model_sku': item.get('model_sku'),
                                            'shopee_discounted_price': discounted_price,
                                            'odoo_total_price': order_line,
                                        }
                                        check_order_line.append(vals)
                            else:
                                self.env['ir.logging'].sudo().create({
                                    'name': '#Shopee: _check_order_line',
                                    'type': 'server',
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'path': 'url',
                                    'message': str(line_payment_json) + 'loi khong co order income',
                                    'func': '_check_order_line',
                                    'line': '0',
                                })

                            line_discount = rec.order_line.filtered(lambda r: r.is_line_coupon_program == True)
                            discount = order_income.get('voucher_from_seller') if order_income.get(
                                'voucher_from_seller') else sum(
                                [res.get('discount_from_voucher_seller') for res in order_income.get('items')])

                            if line_discount:
                                if abs(line_discount.price_total) != discount:
                                    check_order_line.append({
                                        'shopee_seller_discount': discount,
                                        'odoo_discount': abs(line_discount.price_total)
                                    })
                            shopee_total = total_original_price - (
                                        total_original_price - total_discounted_price) - discount
                            if int(rec.amount_total) != int(shopee_total):
                                check_order_line.append({
                                    'shopee_total_original_price': total_original_price,
                                    'shopee_total_discounted_price': total_discounted_price,
                                    'shopee_price_total': shopee_total,
                                })

                            if len(check_order_line) > 0:
                                val_list = {
                                    'order_id': rec.id,
                                    'ma_don_hang': rec.s_shopee_id_order,
                                    'price_detail': check_order_line,
                                    'line_payment_detail': str(line_payment_json),
                                }
                                self.env['ir.logging'].sudo().create({
                                    'name': '#Shopee: _check_order_line',
                                    'type': 'server',
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'path': 'url',
                                    'message': str(val_list),
                                    'func': '_check_order_line',
                                    'line': '0',
                                })
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': '#Shopee: _check_order_line',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'path': 'url',
                                'message': str(line_payment_json) + 'loi khong co order income',
                                'func': '_check_order_line',
                                'line': '0',
                            })
                    else:
                        self.env['ir.logging'].sudo().create({
                            'name': '#Shopee: _check_order_line',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'path': 'url',
                            'message': str(line_payment_json) + 'loi khong co order income',
                            'func': '_check_order_line',
                            'line': '0',
                        })
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': '#Shopee: _check_order_line',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': line_payment_json.get('message'),
                        'func': '_check_order_line',
                        'line': '0',
                    })
            elif rec.is_return_order_shopee and rec.s_shopee_return_sn:
                check_order_return = []
                api_return = self.env['sale.order'].sudo()._get_detail_so_return_shopee(rec.s_shopee_return_sn)
                if api_return:
                    if api_return.get('item'):
                        voucher_seller_items = 0
                        items = api_return.get('item')
                        for item in items:
                            if item.get('variation_sku'):
                                variation_sku = item.get('variation_sku')
                                lines = rec.order_line.filtered(lambda
                                                                    r: r.product_id.default_code == variation_sku) if "," not in variation_sku else rec.order_line.filtered(
                                    lambda r: r.product_id.marketplace_sku != False and (
                                        r.product_id.marketplace_sku.encode('ascii', 'ignore')).decode("utf-8") == (
                                                  variation_sku.encode('ascii', 'ignore')).decode("utf-8"))
                                # line = line[0]
                            else:
                                item_sku = item.get('item_sku')
                                lines = rec.order_line.filtered(lambda
                                                                    r: r.product_id.default_code == item_sku) if "," not in item_sku else rec.order_line.filtered(
                                    lambda r: (r.product_id.marketplace_sku.encode('ascii', 'ignore')).decode(
                                        "utf-8") == (item_sku.encode('ascii', 'ignore')).decode("utf-8"))
                                # line = line[0]
                            if lines:
                                total_qty_line = abs(sum(lines.mapped('product_uom_qty')))
                                if total_qty_line != item.get('amount'):
                                    vals = {
                                        'shopee_sku': item.get('variation_sku') if item.get(
                                            'variation_sku') else item.get('item_sku'),
                                        'shopee_qty_product': item.get('amount'),
                                        'odoo_qty_product': total_qty_line,
                                    }
                                    check_order_return.append(vals)
                                elif abs(sum(lines.mapped('price_total'))) != abs(
                                        item.get('item_price') * item.get('amount')):
                                    vals = {
                                        'shopee_sku': item.get('variation_sku') if item.get(
                                            'variation_sku') else item.get('item_sku'),
                                        'shopee_price_total_line': abs(item.get('item_price') * item.get('amount')),
                                        'odoo_price_total_line': abs(sum(lines.mapped('price_total'))),
                                    }
                                    check_order_return.append(vals)
                            if int(sum(rec.order_line.mapped('price_total'))) != int(rec.amount_total):
                                vals = {
                                    'shopee_sku': item.get('variation_sku') if item.get('variation_sku') else item.get(
                                        'item_sku'),
                                    'sum_total_line_odoo': int(sum(rec.order_line.mapped('price_total'))),
                                    'amount_total_odoo': int(rec.amount_total),
                                }
                                check_order_return.append(vals)
                if len(check_order_return) > 0:
                    val_list = {
                        'order_id': rec.id,
                        'ma_tra_hang': rec.s_shopee_return_sn,
                        'return_detail': check_order_return,
                        'api_return': str(api_return),
                    }
                    self.env['ir.logging'].sudo().create({
                        'name': '#Shopee: _check_order_return',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': str(val_list),
                        'func': '_check_order_return',
                        'line': '0',
                    })

    def _compute_so_return_shopee(self):
        for rec in self:
            order_line_total = sum(rec.order_line.mapped('price_total'))
            amount_total = rec.amount_total
            if order_line_total != amount_total:
                if rec.s_shopee_return_sn:
                    return_detail = self.env['sale.order'].sudo()._get_detail_so_return_shopee(rec.s_shopee_return_sn)
                    if return_detail is not None:
                        order_delivery = rec.order_line.filtered(lambda r: r.is_delivery == True)
                        line_promotion = rec.order_line.filtered(lambda r: r.is_line_coupon_program == True)
                        total_price_product = sum([res.get('item_price') for res in return_detail.get('item')])
                        if return_detail.get('refund_amount') < rec.return_order_id.amount_total:
                            discount_return = float(total_price_product) - float(return_detail.get('refund_amount'))
                            if line_promotion:
                                line_promotion.sudo().write({
                                    'price_unit': - discount_return,
                                    's_lst_price': discount_return,
                                    'product_uom_qty': -1
                                })
                            if len(order_delivery) > 0:
                                for remove_product in order_delivery:
                                    rec.sudo().write({
                                        'order_line': [(2, remove_product.id)]
                                    })
                        elif return_detail.get('refund_amount') == rec.return_order_id.amount_total:
                            if line_promotion:
                                line_promotion.sudo().write({
                                    's_lst_price': line_promotion.price_unit,
                                    'product_uom_qty': -1
                                })
                            if order_delivery:
                                order_delivery.sudo().write({
                                    's_lst_price': order_delivery.price_unit,
                                    'product_uom_qty': -1
                                })

    def _compute_so_shopee(self):
        for rec in self:
            line_delivery = rec.order_line.filtered(lambda r: r.is_delivery == True and r.name != "phi bao hiem")
            line_promotion = rec.order_line.filtered(lambda r: r.is_line_coupon_program == True)
            product = rec.order_line.filtered(lambda r: r.is_delivery == False and r.is_line_coupon_program == False)
            price_total_product = sum([res.price_total for res in product])
            api_detail = self.env['sale.order'].sudo().get_order_details_shopee(rec.s_shopee_id_order)
            api_detail_json = api_detail.json()
            if api_detail.status_code != 200:
                raise ValidationError("invalid access token")
            shipping_carrier = ''
            if api_detail_json.get('response') and api_detail_json.get('response').get('order_list'):
                order_list = api_detail_json.get('response')['order_list']
                if order_list:
                    total_amout = api_detail_json.get('response')['order_list'][0].get('total_amount')
                    phi_bao_hiem = 0
                    if api_detail.status_code == 200:
                        if api_detail_json.get('response'):
                            if api_detail_json.get('response')['order_list'][0].get('package_list'):
                                shipping_carrier = api_detail_json.get('response')['order_list'][0].get('package_list')[
                                    0].get(
                                    'shipping_carrier')
                            else:
                                shipping_carrier = 'Phí giao Hàng'
                    shipping = self.env['sale.order'].sudo().get_escrow_detail(rec.s_shopee_id_order)
                    shipping_json = shipping.json()
                    if shipping.status_code == 200:
                        if shipping_json.get('response'):
                            response = shipping_json.get('response')
                            if response.get('order_income'):
                                order_income = response.get('order_income')
                                if order_income.get('shopee_discount'):
                                    self.env['ir.logging'].sudo().create({
                                        'name': '#Shopee: _compute_so_shopee shopee_discount',
                                        'type': 'server',
                                        'dbname': 'boo',
                                        'level': 'ERROR',
                                        'path': 'url',
                                        'message': str(rec.id) + str(api_detail_json),
                                        'func': '_compute_so_shopee',
                                        'line': '0',
                                    })
                                if order_income.get('buyer_paid_shipping_fee'):
                                    shipping_price = abs(order_income.get('buyer_paid_shipping_fee'))
                                    phi_bao_hiem = abs(
                                        order_income.get('final_product_protection')) if order_income.get(
                                        'final_product_protection') else 0
                                    line_phi_bao_hiem = rec.order_line.filtered(
                                        lambda r: r.is_delivery == True and r.name == "phi bao hiem")
                                    if phi_bao_hiem and not line_phi_bao_hiem:
                                        phi_bao_hiem_id, param_phi_bao_hiem = self.env[
                                            'sale.order'].sudo()._get_shipping_method_shopee("phi bao hiem",
                                                                                             phi_bao_hiem)
                                        add_phi_bao_hiem = rec.sudo().write({
                                            'order_line': [(0, 0, param_phi_bao_hiem)]
                                        })
                                        if add_phi_bao_hiem:
                                            rec.order_line.filtered(
                                                lambda
                                                    r: r.is_delivery == True and r.name == "phi bao hiem").sudo().write(
                                                {
                                                    's_lst_price': phi_bao_hiem
                                                })
                                    discount_price = (price_total_product + shipping_price + phi_bao_hiem) - total_amout
                                    if shipping_price != abs(line_delivery.price_total):
                                        if shipping_price != 0:
                                            if line_delivery:
                                                line_delivery.sudo().write({
                                                    'price_unit': shipping_price,
                                                    's_lst_price': shipping_price
                                                })
                                            else:
                                                carrier_id, order_line_delivery = self.env[
                                                    'sale.order'].sudo()._get_shipping_method_shopee(shipping_carrier,
                                                                                                     shipping_price)
                                                deilvery = rec.sudo().write({
                                                    'order_line': [(0, 0, order_line_delivery)]
                                                })
                                                if deilvery:
                                                    rec.order_line.filtered(
                                                        lambda r: r.is_delivery == True).sudo().write({
                                                        's_lst_price': shipping_price
                                                    })

                                                discount_price = (
                                                                         price_total_product + shipping_price + phi_bao_hiem) - total_amout
                                                if discount_price != 0 and not line_promotion:
                                                    get_promotion = self.env[
                                                        'sale.order'].sudo()._get_line_discount_shopee(
                                                        discount_price)
                                                    if get_promotion:
                                                        promotion = rec.sudo().write({
                                                            'order_line': [(0, 0, get_promotion)]
                                                        })
                                                        if promotion:
                                                            rec.order_line.filtered(
                                                                lambda
                                                                    r: r.is_line_coupon_program == True).sudo().write({
                                                                's_lst_price': discount_price
                                                            })
                                        elif shipping_price == 0:
                                            if line_delivery:
                                                line_delivery.sudo().write({
                                                    'product_uom_qty': 0,
                                                    'price_unit': shipping_price,
                                                    's_lst_price': shipping_price
                                                })
                                        if line_promotion:
                                            if discount_price != 0:
                                                line_promotion.sudo().write({
                                                    'price_unit': - discount_price,
                                                    's_lst_price': discount_price
                                                })
                                            else:
                                                line_promotion.sudo().write({
                                                    'product_uom_qty': 0,
                                                    'price_unit': - discount_price,
                                                    's_lst_price': discount_price
                                                })
                                else:
                                    total_discount_shopee = 0
                                    for order_income_id in order_income.get('items'):
                                        total_discount_shopee += order_income_id.get(
                                            'discount_from_voucher_seller') + order_income_id.get(
                                            'discount_from_voucher_shopee') + order_income_id.get(
                                            'discount_from_coin')
                                    phi_bao_hiem = abs(
                                        order_income.get('final_product_protection')) if order_income.get(
                                        'final_product_protection') else 0
                                    total_shipping_value = total_amout + total_discount_shopee + phi_bao_hiem - price_total_product
                                    if line_delivery:
                                        line_delivery.sudo().write({
                                            'product_uom_qty': 0
                                        })
                                    elif total_shipping_value > 0 and shipping_carrier:
                                        carrier_id, order_line_delivery = self.env[
                                            'sale.order'].sudo()._get_shipping_method_shopee(shipping_carrier,
                                                                                             total_shipping_value)
                                        s_carrier_id = self.env['delivery.carrier'].browse(carrier_id)
                                        rec['s_carrier_id'] = s_carrier_id
                                        if s_carrier_id.product_id:
                                            s_carrier_id.product_id.sudo().write({
                                                'lst_price': total_shipping_value,
                                                'la_phi_ship_hang_m2': True
                                            })
                                            rec.sudo().write({
                                                'order_line': [(0, 0, {
                                                    'product_id': s_carrier_id.product_id.id,
                                                    'is_delivery': True,
                                                })]
                                            })
                                    discount_price = (
                                                                 price_total_product + phi_bao_hiem) - total_amout + total_shipping_value
                                    if line_promotion:
                                        if discount_price != 0:
                                            line_promotion.sudo().write({
                                                'price_unit': - discount_price,
                                                's_lst_price': discount_price
                                            })
                                        else:
                                            line_promotion.sudo().write({
                                                'product_uom_qty': 0,
                                                'price_unit': - discount_price,
                                                's_lst_price': discount_price
                                            })
                    else:
                        raise ValidationError("invalid access token")
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': '#Shopee: _compute_so_shopee',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': str(rec.id) + str(api_detail_json),
                        'func': '_compute_so_shopee',
                        'line': '0',
                    })
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: _compute_so_shopee',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': str(rec.id) + str(api_detail_json),
                    'func': '_compute_so_shopee',
                    'line': '0',
                })

    def check_so_shopee(self):
        check = []
        for rec in self:
            line_delivery = rec.order_line.filtered(lambda r: r.is_delivery == True and r.name != "phi bao hiem")
            line_promotion = rec.order_line.filtered(lambda r: r.is_line_coupon_program == True)
            product = rec.order_line.filtered(lambda r: r.is_delivery == False and r.is_line_coupon_program == False)
            price_total_product = sum([res.price_total for res in product])
            phi_bao_hiem = 0
            api_detail = self.env['sale.order'].sudo().get_order_details_shopee(rec.s_shopee_id_order)
            api_detail_json = api_detail.json()
            # if api_detail.status_code == 200:
            #     if api_detail_json.get('response'):
            #         shipping_carrier = api_detail_json.get('response')['order_list'][0].get('package_list')[0].get('shipping_carrier')
            shipping = self.env['sale.order'].sudo().get_escrow_detail(rec.s_shopee_id_order)
            if shipping.status_code != 200:
                raise ValidationError("invalid access token")
            shipping_json = shipping.json()
            if shipping.status_code == 200:
                if shipping_json.get('response'):
                    response = shipping_json.get('response')
                    if response.get('order_income'):
                        order_income = response.get('order_income')
                        if order_income.get('buyer_paid_shipping_fee'):
                            shipping_price = abs(order_income.get('buyer_paid_shipping_fee'))
                            phi_bao_hiem = abs(order_income.get('final_product_protection')) if order_income.get(
                                'final_product_protection') else 0
                            line_phi_bao_hiem = rec.order_line.filtered(
                                lambda r: r.is_delivery == True and r.name == "phi bao hiem")
                            discount_price = (price_total_product + shipping_price + phi_bao_hiem) - rec.amount_total
                            if shipping_price:
                                if line_delivery:
                                    if shipping_price != abs(line_delivery.price_total):
                                        check.append({
                                            's_shopee_id_order': rec.s_shopee_id_order,
                                            'shipping_price': shipping_price,
                                            'final_shipping_fee': order_income.get('final_shipping_fee')
                                        })
                                    else:
                                        if line_promotion:
                                            if discount_price != abs(line_promotion.price_total):
                                                check.append({
                                                    's_shopee_id_order': rec.s_shopee_id_order,
                                                    'discount_price': discount_price,
                                                    'final_shipping_fee': order_income.get('final_shipping_fee')
                                                })
                                else:
                                    check.append({
                                        's_shopee_id_order': rec.s_shopee_id_order,
                                        'shipping_price': shipping_price,
                                        'final_shipping_fee': order_income.get('final_shipping_fee')
                                    })
                            else:
                                if line_delivery:
                                    check.append({
                                        's_shopee_id_order': rec.s_shopee_id_order,
                                        'shipping_price': shipping_price,
                                        'final_shipping_fee': order_income.get('final_shipping_fee')
                                    })
                                else:
                                    if line_promotion:
                                        if discount_price != abs(line_promotion.price_total):
                                            check.append({
                                                's_shopee_id_order': rec.s_shopee_id_order,
                                                'discount_price': discount_price,
                                                'final_shipping_fee': order_income.get('final_shipping_fee')
                                            })
                            if phi_bao_hiem:
                                if line_phi_bao_hiem:
                                    if abs(line_phi_bao_hiem.price_total) != phi_bao_hiem:
                                        check.append({
                                            's_shopee_id_order': rec.s_shopee_id_order,
                                            'phi_bao_hiem': phi_bao_hiem,
                                            'final_shipping_fee': order_income.get('final_shipping_fee')
                                        })
                                else:
                                    check.append({
                                        's_shopee_id_order': rec.s_shopee_id_order,
                                        'phi_bao_hiem': phi_bao_hiem,
                                        'final_shipping_fee': order_income.get('final_shipping_fee')
                                    })
            else:
                print(shipping.status_code)
        print("1111111111111111111111", check)

    def _mass_compute_do_shopee(self):
        SO_done = self.env['sale.order'].sudo().search(
            [('s_shopee_is_order', '=', True), ('sale_order_status', 'in', ['hoan_thanh'])])
        SO_huy = self.env['sale.order'].sudo().search(
            [('s_shopee_is_order', '=', True), ('sale_order_status', 'in', ['huy'])])
        if len(SO_done) > 0:
            for rec in SO_done:
                if rec.picking_ids.state in ["confirmed"]:
                    rec.picking_ids.action_assign()
                if rec.picking_ids.state not in ["done"]:
                    rec.picking_ids.action_set_quantities_to_reservation()
                    rec.picking_ids.button_validate()
        if len(SO_huy) > 0:
            for r in SO_huy:
                if rec.picking_ids.state not in ["huy"]:
                    picking_done_ids = r.picking_ids.filtered(
                        lambda p: p.state in ['done'] and p.transfer_type == 'out')
                    if picking_done_ids:
                        for picking_done_id in picking_done_ids:
                            return_picking_old_id = r.picking_ids.filtered(
                                lambda p: picking_done_id.name in p.origin)
                            if return_picking_old_id:
                                break
                            # Tao lenh return DO
                            return_picking_id = self.env['stock.return.picking'].create(
                                {'picking_id': picking_done_id.id})
                            # Them san pham vao return DO
                            return_picking_id.sudo()._onchange_picking_id()
                            # tao phieu return DO
                            if len(return_picking_id.product_return_moves) > 0:
                                result_return_picking = return_picking_id.sudo().create_returns()
                                if result_return_picking:
                                    picking_return = r.picking_ids.filtered(
                                        lambda r: r.id == result_return_picking.get('res_id'))
                                    if picking_return.state == 'assigned':
                                        picking_return.action_set_quantities_to_reservation()
                                        # picking_return.button_validate()
                                    boo_do_return = self.env['stock.picking'].search(
                                        [('id', '=', result_return_picking.get('res_id'))])
                                    if boo_do_return and not boo_do_return.is_boo_do_return:
                                        boo_do_return.write({'is_boo_do_return': True})
                    else:
                        picking_not_done_ids = r.picking_ids.filtered(
                            lambda p: p.state not in ['done'] and p.transfer_type == 'out')
                        if picking_not_done_ids:
                            for picking_not_done_id in picking_not_done_ids:
                                picking_not_done_id.action_cancel()
                        r.sudo().with_context(api_cancel_do=True)._action_cancel()

    @api.depends('s_shopee_is_order')
    def _compute_source_ecommerce(self):
        res = super(SSaleOrder, self)._compute_source_ecommerce()
        for r in self:
            if r.s_shopee_is_order:
                r.sudo().source_ecommerce = "Shopee"
        return res

    @api.depends('s_shopee_is_order')
    def _compute_invisible_context(self):
        for rec in self:
            rec.is_invisible_ecommerce = False
            if rec.s_shopee_is_order and not rec.is_invisible_ecommerce:
                rec.is_invisible_ecommerce = True

    @api.depends('s_shopee_is_order')
    def _compute_is_ecommerce_order(self):
        res = super(SSaleOrder, self)._compute_is_ecommerce_order()
        for rec in self:
            if (rec.s_shopee_is_order or rec.return_order_id.s_shopee_is_order) and not rec.is_ecommerce_order:
                rec.sudo().write({
                    'is_ecommerce_order': True
                })
        return res

    @api.depends('state', 'picking_ids.state', 'marketplace_shopee_order_status')
    def _compute_sale_order_state(self):
        res = super(SSaleOrder, self)._compute_sale_order_state()
        for rec in self:
            if rec.s_shopee_is_order == True:
                if rec.marketplace_shopee_order_status in ['UNPAID', 'READY_TO_SHIP']:
                    rec.sudo().sale_order_status = 'moi'
                elif rec.marketplace_shopee_order_status in ['PROCESSED']:
                    rec.sudo().sale_order_status = 'dang_xu_ly'
                elif rec.marketplace_shopee_order_status in ['RETRY_SHIP']:
                    rec.sudo().sale_order_status = 'dang_xu_ly'
                elif rec.marketplace_shopee_order_status in ['SHIPPED']:
                    rec.sudo().sale_order_status = 'dang_giao_hang'
                elif rec.marketplace_shopee_order_status in ['TO_RETURN']:
                    rec.sudo().sale_order_status = 'hoan_thanh'
                elif rec.marketplace_shopee_order_status in ['TO_CONFIRM_RECEIVE', 'COMPLETED'] and \
                        rec.sudo().sale_order_status not in ['hoan_thanh_1_phan', 'huy', 'giao_hang_that_bai']:
                    rec.sudo().sale_order_status = 'hoan_thanh'
                elif rec.marketplace_shopee_order_status in ['CANCELLED'] and \
                        rec.sudo().sale_order_status not in ['hoan_thanh_1_phan', 'giao_hang_that_bai']:
                    rec.sudo().sale_order_status = 'huy'

        return res

    def get_order_details_shopee(self, order_sn_list):
        url_api = "/api/v2/order/get_order_detail"
        param = {
            "order_sn_list": order_sn_list,
            "response_optional_fields": "[buyer_user_id,buyer_username,estimated_shipping_fee,recipient_address,actual_shipping_fee ,goods_to_declare,note,note_update_time,item_list,pay_time,dropshipper,dropshipper_phone,split_up,buyer_cancel_reason,cancel_by,cancel_reason,actual_shipping_fee_confirmed,buyer_cpf_id,fulfillment_flag,pickup_done_time,package_list,shipping_carrier,payment_method,total_amount,buyer_username,invoice_data]"
        }
        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=url_api, param=param)
        return req

    def get_escrow_detail(self, order_sn):
        url_api = "/api/v2/payment/get_escrow_detail"
        param = {
            "order_sn": order_sn,
        }
        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=url_api, param=param)
        return req

    def _get_shipping_method_shopee(self, shipping_carrier=False, shipping_price=False, sale_order_id=False):
        order_line_delivery = False
        carrier_id = False
        if shipping_carrier and shipping_price:
            shipping_method = self.env['delivery.carrier'].sudo().search([('name', 'ilike', shipping_carrier)],
                                                                         limit=1)
            if shipping_method:
                carrier_id = shipping_method.id
                shipping_method_product_old_value = self.env['product.product'].sudo().search([
                    ('id', '=', shipping_method.product_id.id)
                ])
                shipping_method_product_old_value.write({
                    'lst_price': float(shipping_price) if shipping_price else 0,
                    'la_phi_ship_hang_m2': True
                })
                if not shipping_method.product_id:
                    raise ValidationError('Product service does not exits!')
                if float(shipping_price) > 0:
                    order_line_delivery = {
                        "product_id": shipping_method.product_id.id,
                        "product_uom_qty": 1,
                        "price_unit": shipping_method_product_old_value.lst_price,
                        "s_lst_price": shipping_method_product_old_value.lst_price,
                        "is_delivery": True,
                    }
            else:
                shipping_method_product_new_value = self.env['product.product'].sudo().create({
                    'name': shipping_carrier,
                    'detailed_type': 'service',
                    'lst_price': float(shipping_price) if shipping_price else 0,
                    'la_phi_ship_hang_m2': True
                })
                if shipping_method_product_new_value:
                    shipping_method_new = self.env['delivery.carrier'].sudo().create({
                        'name': shipping_carrier,
                        'delivery_type': 'fixed',
                        # 'invoice_policy': 'real',
                        'product_id': shipping_method_product_new_value.id
                    })
                    carrier_id = shipping_method_new.id
                    if shipping_method_product_new_value.lst_price > 0:
                        order_line_delivery = {
                            "product_id": shipping_method_new.product_id.id,
                            "product_uom_qty": 1,
                            "price_unit": shipping_method_product_new_value.lst_price,
                            "s_lst_price": shipping_method_product_new_value.lst_price,
                            "is_delivery": True,
                        }
        return carrier_id, order_line_delivery

    def _get_line_discount_shopee(self, discount_price=False, ):
        order_line = False
        if discount_price:
            product_coupon_program = self.env['product.product'].sudo().search([('name', 'ilike', 'Discount Shopee')],
                                                                               limit=1)
            if product_coupon_program:
                product_coupon_program.write({
                    'lst_price': float(discount_price) if discount_price else 0,
                })
                order_line = {
                    "product_id": product_coupon_program.id,
                    "product_uom_qty": 1,
                    "price_unit": -float(discount_price) if discount_price else 0,
                    "s_lst_price": -float(discount_price) if discount_price else 0,
                    "is_line_coupon_program": True,
                    "is_ecommerce_reward_line": True,
                }
            else:
                product_coupon_program = self.env['product.product'].sudo().create({
                    'name': 'Discount Shopee',
                    'detailed_type': 'service',
                    'lst_price': float(discount_price) if discount_price else 0,
                })
                if product_coupon_program:
                    if product_coupon_program.lst_price > 0:
                        order_line = {
                            "product_id": product_coupon_program.id,
                            "product_uom_qty": 1,
                            "price_unit": -(product_coupon_program.lst_price),
                            "s_lst_price": -(product_coupon_program.lst_price),
                            "is_line_coupon_program": True,
                            "is_ecommerce_reward_line": True,
                        }
        return order_line

    def btn_infor_customer_shopee(self):
        view = self.env.ref('advanced_integrate_shopee.infor_customer_shopee_type_form_view')
        return {
            'name': _('Cập nhật'),
            'type': 'ir.actions.act_window',
            'res_model': 'mass.action.infor.customer.shopee',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {'default_s_shopee_id_order': self.id}
        }

    def _get_return_list_shopee(self, update_time):
        url_endpoint = "/api/v2/returns/get_return_list"
        date_time = datetime.fromtimestamp(update_time) + timedelta(seconds=25200)
        date_time_to = date_time + timedelta(minutes=1)
        unix_timestamp_to = int(time.mktime(date_time_to.timetuple()))
        unix_timestamp = int(time.mktime(date_time.timetuple()))
        param = {
            "page_no": 0,
            "page_size": 100,
            "create_time_from": update_time,
            "create_time_to": unix_timestamp_to
        }
        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=url_endpoint, param=param)
        return req

    def _get_detail_so_return_shopee(self, return_sn):
        url_endpoint = "/api/v2/returns/get_return_detail"
        param = {
            "return_sn": return_sn
        }
        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=url_endpoint, param=param)
        req_json = req.json()
        if req.status_code == 200:
            if not req_json.get('error'):
                return req_json['response']
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: _get_detail_so_return_shopee',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': req_json.get('message'),
                    'func': '_get_detail_so_return_shopee',
                    'line': '0',
                })
        else:
            self.env['ir.config_parameter'].sudo().set_param(
                'advanced_integrate_shopee.is_error_token_shopee', 'True')
            self.env['ir.logging'].sudo().create({
                'name': '#Shopee: _get_detail_so_return_shopee',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': req_json.get('message'),
                'func': '_get_detail_so_return_shopee',
                'line': '0',
            })

    def _amount_all(self):
        res = super(SSaleOrder, self)._amount_all()
        for order in self:
            if order.is_return_order_shopee and not order.amount_total:
                order.amount_total = sum(order.order_line.mapped('price_total'))
        return res

    def create_return_sale_order_shopee(self):
        for rec in self:
            if len(rec.order_line) > 0:
                so_line = []
                for line in rec.order_line:
                    so_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'product_uom_qty': -line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'price_unit': line.price_unit,
                        'refunded_orderline_id': line.id,
                        'm2_is_global_discount': line.m2_is_global_discount if line.m2_is_global_discount else False,
                        'm2_total_line_discount': - line.m2_total_line_discount if line.m2_total_line_discount else 0,
                        'gift_card_id': line.gift_card_id.id if line.gift_card_id else False,
                        'coupon_program_id': line.coupon_program_id.id if line.coupon_program_id else False,
                        # 'return_po_line_id': line.id,
                        'tax_id': [(6, 0, line.tax_id.ids)] if line.tax_id else False,
                        'is_line_coupon_program': line.is_line_coupon_program,
                        'is_ecommerce_reward_line': line.is_ecommerce_reward_line,
                        'is_delivery': line.is_delivery,
                    }))
                sale_order = {
                    'partner_id': rec.partner_id.id,
                    'return_order_id': rec.id,
                    # 'is_magento_order': rec.is_magento_order,
                    'payment_method': rec.payment_method if rec.payment_method else False,
                    'order_line': so_line,
                    'is_return_order': True,
                    # 'name': 'Đổi trả đơn ' + rec.name,
                }
                source = self.env.ref('advanced_sale.utm_source_magento_order').id
                if rec.is_magento_order and rec.source_id.id == source:
                    sale_order.update({
                        'source_id': source
                    })
                sale_order_id = self.env['sale.order'].sudo().create(sale_order)
                sale_order_id.name = sale_order_id.name + ' - Đổi trả đơn ' + rec.name
                # if sale_order_id:
                #     rec.sudo().write({
                #         'return_order': sale_order_id.id,
                #     })
                action = self.env.ref('sale.action_quotations_with_onboarding').sudo().read()[0]
                form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
                action['views'] = form_view
                action['context'] = {'edit': True}
                action['res_id'] = sale_order_id.sudo().id
                return action

    def _create_so_return_shopee(self, ordersn, order_return):
        try:
            order = self.env['sale.order'].sudo().search(
                [('s_shopee_id_order', '=', ordersn), ('is_return_order_shopee', '=', False)], limit=1)
            search_order_return = order.return_order_ids.filtered(
                lambda r: r.s_shopee_return_sn == order_return.get('return_sn'))
            warehouse = self.env['stock.warehouse'].sudo().search(
                [('e_commerce', '=', 'shopee'), ('s_shopee_is_mapping_warehouse', '=', True)])
            qty_product_return = sum([res.get('amount') for res in order_return.get('item')])
            total_price_product = sum([res.get('item_price') for res in order_return.get('item')])
            qty_product = sum(order.order_line.filtered(
                lambda r: r.is_delivery == False and r.is_line_coupon_program == False).mapped('product_uom_qty'))
            order_delivery = order.order_line.filtered(lambda r: r.is_delivery == True)

            # price_total_so = sum([line.price_unit * line.product_uom_qty for line in order.order_line if
            #                       not line.m2_is_global_discount and not line.coupon_program_id and not line.is_delivery and not line.gift_card_id
            #                       and not line.is_ecommerce_reward_line and not line.is_line_coupon_program])
            #
            # boo_total_discount_percentage = total_discount * (((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) *line.discount / 100) / price_total_so)

            if order_return.get('status') in ['PROCESSING', 'CLOSED', 'CANCELLED', 'ACCEPTED',
                                              'REFUND_PAID'] and not search_order_return:
                if len(order_return.get('item')) > 0:
                    id_return_order_new_create = order.sudo().create_return_sale_order()
                    so_return_and_refund = order.return_order_ids.filtered(
                        lambda r: r.id == id_return_order_new_create.get('res_id'))
                    product_return = so_return_and_refund.order_line.filtered(
                        lambda r: r.is_delivery == False and r.is_line_coupon_program == False).mapped('id')
                    line_delivery = so_return_and_refund.order_line.filtered(lambda r: r.is_delivery == True)
                    line_promotion = so_return_and_refund.order_line.filtered(
                        lambda r: r.is_line_coupon_program == True)
                    if so_return_and_refund:
                        if qty_product_return < qty_product:
                            discount = 0
                            for rec_return in order_return.get('item'):
                                amount = rec_return.get('amount')
                                if rec_return.get('variation_sku'):
                                    variation_sku = rec_return.get('variation_sku')
                                    lines = so_return_and_refund.order_line.filtered(lambda
                                                                                         r: r.product_id.default_code == variation_sku) if "," not in variation_sku else so_return_and_refund.order_line.filtered(
                                        lambda r: r.product_id.marketplace_sku != False and (
                                            r.product_id.marketplace_sku.encode('ascii', 'ignore')).decode("utf-8") == (
                                                      variation_sku.encode('ascii', 'ignore')).decode("utf-8"))
                                    # line = line[0]
                                else:
                                    item_sku = rec_return.get('item_sku')
                                    lines = so_return_and_refund.order_line.filtered(lambda
                                                                                         r: r.product_id.default_code == item_sku) if "," not in item_sku else so_return_and_refund.order_line.filtered(
                                        lambda r: (r.product_id.marketplace_sku.encode('ascii', 'ignore')).decode(
                                            "utf-8") == (item_sku.encode('ascii', 'ignore')).decode("utf-8"))
                                    # line = line[0]

                                if lines:
                                    # total_qty_line_refund = sum(lines.mapped('product_uom_qty'))
                                    for line in lines:
                                        if amount > 0:
                                            if abs(line.product_uom_qty) >= abs(amount):
                                                discount += (abs(line.boo_total_discount_percentage) / abs(
                                                    line.product_uom_qty)) * amount
                                                line.product_uom_qty = -float(amount)
                                                amount -= abs(line.product_uom_qty)
                                                product_return.remove(line.id)
                                            else:
                                                discount += (abs(line.boo_total_discount_percentage) / abs(
                                                    line.product_uom_qty)) * abs(line.product_uom_qty)
                                                amount -= abs(line.product_uom_qty)
                                                product_return.remove(line.id)

                            if len(product_return) > 0:
                                for remove_product in product_return:
                                    so_return_and_refund.sudo().write({
                                        'order_line': [(2, remove_product)]
                                    })
                            if discount != 0:
                                if line_promotion:
                                    line_promotion.sudo().write({
                                        'price_unit': -discount,
                                        's_lst_price': -discount
                                    })

                        elif qty_product_return == qty_product:
                            if line_promotion:
                                line_promotion.sudo().write({
                                    's_lst_price': -line_promotion.price_unit
                                })

                        so_return_and_refund.sudo().write({
                            'is_return_order_shopee': True,
                            'refund_total_shopee': float(sum(so_return_and_refund.order_line.mapped('price_total'))),
                            'source_id': self.env.ref('advanced_integrate_shopee.utm_source_shopee').id,
                            's_shopee_status_return': order_return.get('status'),
                            'warehouse_id': warehouse.id,
                            's_shopee_return_sn': order_return.get('return_sn'),
                            's_shopee_id_order': ordersn
                        })
                        so_return_and_refund.sudo().action_confirm()
                        if order_return.get('create_time'):
                            so_return_and_refund.sudo().write({
                                'date_order': datetime.fromtimestamp(int(order_return.get('create_time'))),
                            })

                    else:
                        self.env['ir.logging'].sudo().create({
                            'name': '#Shopee: _create_so_return_shopee',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'path': 'url',
                            'message': "chưa tạo được đơn return",
                            'func': '_create_so_return_shopee',
                            'line': '0',
                        })
            elif order_return.get('status') in ['CLOSED', 'CANCELLED', 'ACCEPTED',
                                                'REFUND_PAID'] and search_order_return:
                search_order_return.sudo().write({
                    's_shopee_status_return': order_return.get('status'),
                })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': '#Shopee: _create_so_return_shopee',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': '_create_so_return_shopee',
                'line': '0',
            })

    def _create_payload_order_shopee(self, orders_detail):
        for rec in orders_detail.get('order_list'):
            pay_load = {
                "code": 3,
                "data": {
                    "items": [],
                    "ordersn": rec.get('order_sn'),
                    "status": rec.get('order_status'),
                    "update_time": rec.get('update_time')
                }
            }
            return pay_load, rec.get('order_sn')

    def _action_get_order_shopee_amount_total_error(self):
        # Cron check SO shopee lệch chi tiết đơn hàng
        order_shopee_amount_total_error = []
        order_shopee_ids = self.search([('s_shopee_is_order', '=', True)])
        if order_shopee_ids:
            for order_shopee_id in order_shopee_ids:
                order_line_shopee_ids = self.get_order_details_shopee(order_shopee_id.s_shopee_id_order)
                if order_line_shopee_ids:
                    if order_line_shopee_ids.get('order_list'):
                        for r in order_line_shopee_ids.get('order_list'):
                            if (order_shopee_id.amount_total != r.get('total_amount') and
                                    order_shopee_id.name not in order_shopee_amount_total_error):
                                order_shopee_amount_total_error.append(order_shopee_id.name)
        print(order_shopee_amount_total_error)

    def compute_sale_order_shopee_error(self):
        for r in self:
            if r.id == 20618:
                so_total_amount = 0
                if r.order_line:
                    for line_id in r.order_line:
                        if line_id.product_id.detailed_type == 'product':
                            line_id.sudo().write({
                                'price_unit': line_id.s_lst_price
                            })
                        so_total_amount += line_id.s_lst_price
                if so_total_amount > 685156:
                    discount_shopee_price = so_total_amount - 685156
                    discount_line_shopee = self._get_line_discount_shopee(discount_shopee_price)
                    if discount_line_shopee:
                        r.order_line = [(0, 0, discount_line_shopee)]

    def check_order_status(self, data, sale_order):
        if data['status'] == "UNPAID" and sale_order.marketplace_shopee_order_status not in ['READY_TO_SHIP',
                                                                                             'PROCESSED', 'RETRY_SHIP',
                                                                                             'SHIPPED',
                                                                                             'TO_CONFIRM_RECEIVE',
                                                                                             'IN_CANCEL', 'CANCELLED',
                                                                                             'TO_RETURN', 'COMPLETED']:
            return "UNPAID"
        elif data[
            'status'] == "READY_TO_SHIP" and sale_order.marketplace_shopee_order_status not in [
            'PROCESSED', 'RETRY_SHIP', 'SHIPPED', 'TO_CONFIRM_RECEIVE', 'IN_CANCEL', 'CANCELLED', 'TO_RETURN',
            'COMPLETED']:
            return "READY_TO_SHIP"
        elif data[
            'status'] == "PROCESSED" and sale_order.marketplace_shopee_order_status not in [
            'SHIPPED', 'TO_CONFIRM_RECEIVE', 'IN_CANCEL', 'CANCELLED', 'TO_RETURN', 'COMPLETED']:
            return "PROCESSED"

        elif data[
            'status'] == "RETRY_SHIP" and sale_order.marketplace_shopee_order_status not in [
            'SHIPPED', 'TO_CONFIRM_RECEIVE', 'IN_CANCEL', 'CANCELLED', 'TO_RETURN', 'COMPLETED']:
            return "RETRY_SHIP"
        elif data[
            'status'] == "SHIPPED" and sale_order.marketplace_shopee_order_status not in [
            'TO_CONFIRM_RECEIVE', 'IN_CANCEL', 'CANCELLED', 'TO_RETURN', 'COMPLETED']:
            return "SHIPPED"
        elif data[
            'status'] == "TO_CONFIRM_RECEIVE" and sale_order.marketplace_shopee_order_status not in [
            'IN_CANCEL', 'CANCELLED', 'TO_RETURN', 'COMPLETED']:
            return "TO_CONFIRM_RECEIVE"
        elif data[
            'status'] == "IN_CANCEL" and sale_order.marketplace_shopee_order_status not in [
            'UNPAID', 'SHIPPED', 'TO_CONFIRM_RECEIVE', 'CANCELLED', 'TO_RETURN', 'COMPLETED']:
            return "IN_CANCEL"
        elif data[
            'status'] == "CANCELLED" and sale_order.sudo().sale_order_status not in [
            'giao_hang_that_bai', 'hoan_thanh',
            'da_giao_hang'] and sale_order.marketplace_shopee_order_status not in [
            'TO_CONFIRM_RECEIVE', 'TO_RETURN', 'COMPLETED']:
            return "CANCELLED"
        elif data[
            'status'] == "TO_RETURN" and sale_order.marketplace_shopee_order_status not in [
            'RETRY_SHIP', 'PROCESSED', 'IN_CANCEL', 'CANCELLED']:
            return "TO_RETURN"
        elif data[
            'status'] == "COMPLETED" and sale_order.sudo().sale_order_status not in [
            'hoan_thanh_1_phan', 'giao_hang_that_bai', 'huy']:
            return "COMPLETED"


class SSaleOrderError(models.Model):
    _name = "s.sale.order.shopee.error"
    _inherit = 'mail.activity.mixin'
    _order = 'create_date desc'

    dbname = fields.Char()
    level = fields.Char()
    message = fields.Char()
    return_created = fields.Boolean(default=False, string="Đã tạo lại đơn")
    order_status = fields.Char()
    payload = fields.Char()
    s_shopee_id_order = fields.Char(string="Id Shopee")
    active = fields.Boolean('Active', default=True)
    s_error_token_shopee = fields.Boolean(string='Là đơn hàng shopee lỗi token', default=False)

    def recreating_an_error_order_shopee(self):
        created_error = False
        context = {}
        api_detail = self.env['sale.order'].sudo().get_order_details_shopee(self.s_shopee_id_order)
        api_detail_json = api_detail.json()
        sale_order = self.env['sale.order'].sudo().search([('s_shopee_id_order', '=', self.s_shopee_id_order)], limit=1)
        if api_detail.status_code == 200:
            if not api_detail_json.get('error'):
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: recreating_an_error_order_shopee',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'Order_Detail',
                    'path': 'url',
                    'message': str(api_detail_json),
                    'func': 'recreating_an_error_order_shopee',
                    'line': '0',
                })
                if api_detail_json.get('response'):
                    orders_detail = api_detail_json.get('response')
                    if sale_order:
                        payload, order_sn = self.env['sale.order'].sudo()._create_payload_order_shopee(orders_detail)
                        if payload:
                            if payload.get('data'):
                                data = payload.get('data')
                                order_status = self.env['sale.order'].sudo().check_order_status(data, sale_order)
                                if order_status:
                                    sale_order.sudo().marketplace_shopee_order_status = order_status
                                if sale_order.sudo().marketplace_shopee_order_status in ['TO_CONFIRM_RECEIVE',
                                                                                         'CANCELLED',
                                                                                         'COMPLETED',
                                                                                         'TO_RETURN']:
                                    ###Update completed_date
                                    if not sale_order.completed_date:
                                        sale_order.completed_date = datetime.fromtimestamp(data['update_time'])
                                if sale_order.sudo().marketplace_shopee_order_status == 'TO_RETURN':
                                    list_return = self.env['sale.order'].sudo()._get_return_list_shopee(
                                        update_time=data.get('update_time'))
                                    list_return_json = list_return.json()
                                    if list_return.status_code == 200:
                                        if not list_return_json.get('error'):
                                            if list_return_json.get('response'):
                                                list_order_return = list_return_json.get('response')
                                                if len(list_order_return.get('return')) > 0:
                                                    for order_return in list_order_return.get('return'):
                                                        if order_return.get('order_sn') == self.s_shopee_id_order:
                                                            status_return = order_return.get('status')
                                                            if status_return in ['PROCESSING', 'CLOSED', 'CANCELLED',
                                                                                 'ACCEPTED', 'REFUND_PAID']:
                                                                self.env[
                                                                    'sale.order'].sudo()._create_so_return_shopee(
                                                                    self.s_shopee_id_order, order_return)
                                        else:
                                            created_error = True
                                            context['message'] = str(list_return_json.get('message'))
                                    else:
                                        self.env['ir.config_parameter'].sudo().set_param(
                                            'advanced_integrate_shopee.is_error_token_shopee', 'True')
                                        created_error = True
                                        context['message'] = str(list_return_json.get('message'))
                                if sale_order.marketplace_shopee_order_status in (
                                        "PROCESSED", "RETRY_SHIP", "SHIPPED", "TO_CONFIRM_RECEIVE", "COMPLETED",
                                        "TO_RETURN"):
                                    picking_ids = sale_order.picking_ids.filtered(
                                        lambda p: p.state not in ('done', 'cancel'))
                                    if len(sale_order.picking_ids) > 0 and len(picking_ids) > 0:
                                        for picking in picking_ids:
                                            if picking.state in ["confirmed"]:
                                                picking.action_assign()
                                            if picking.state == 'assigned':
                                                picking.action_set_quantities_to_reservation()
                                                picking.button_validate()

                                status_logistics_shopee = sale_order.picking_ids.filtered(
                                    lambda r: r.transfer_type == 'out').s_shopee_logistics_status
                                # Fake status shipment để test
                                if data.get('test_shipment_status') is not None:
                                    status_logistics_shopee = data.get(
                                        'test_shipment_status').get(
                                        'logistics_status')
                                else:
                                    # Lưu trạng thái DO Shopee
                                    logistics_status = self.env['stock.picking'].sudo()._get_tracking_info(
                                        self.s_shopee_id_order)
                                    if logistics_status is not None:
                                        if status_logistics_shopee != logistics_status.get(
                                                'logistics_status'):
                                            status_logistics_shopee = logistics_status.get(
                                                'logistics_status')
                                if sale_order.marketplace_shopee_order_status == "CANCELLED":
                                    picking_done_ids = sale_order.picking_ids.filtered(
                                        lambda p: p.state in ['done'] and p.transfer_type == 'out')
                                    if picking_done_ids:
                                        for picking_done_id in picking_done_ids:
                                            return_picking_old_id = sale_order.picking_ids.filtered(
                                                lambda p: picking_done_id.name in p.origin)
                                            if return_picking_old_id:
                                                break
                                            # Tao lenh return DO
                                            return_picking_id = self.env['stock.return.picking'].create(
                                                {'picking_id': picking_done_id.id})
                                            # Them san pham vao return DO
                                            return_picking_id.sudo()._onchange_picking_id()
                                            # tao phieu return DO
                                            if len(return_picking_id.product_return_moves) > 0:
                                                result_return_picking = return_picking_id.sudo().create_returns()
                                                if result_return_picking:
                                                    picking_return = sale_order.picking_ids.filtered(
                                                        lambda r: r.id == result_return_picking.get(
                                                            'res_id'))
                                                    if picking_return.state == 'assigned':
                                                        picking_return.action_set_quantities_to_reservation()
                                                        # picking_return.button_validate()
                                                    boo_do_return = self.env['stock.picking'].search(
                                                        [('id', '=', result_return_picking.get('res_id'))])
                                                    if boo_do_return and not boo_do_return.is_boo_do_return:
                                                        boo_do_return.write({'is_boo_do_return': True})
                                    else:
                                        picking_not_done_ids = sale_order.picking_ids.filtered(
                                            lambda p: p.state not in ['done',
                                                                      'cancel'] and p.transfer_type == 'out')
                                        if picking_not_done_ids:
                                            for picking_not_done_id in picking_not_done_ids:
                                                picking_not_done_id.action_cancel()
                                        sale_order.sudo().with_context(api_cancel_do=True)._action_cancel()
                                    sale_order.sudo().write({
                                        'sale_order_status': 'huy'
                                    })
                                if not created_error:
                                    self.sudo().write({
                                        'return_created': True
                                    })
                        # else:
                        #     created_error = True
                        #     context['message'] = "Chưa có đơn hàng shopee id: %s" % str(self.s_shopee_id_order)
                    elif not sale_order:
                        customer_shopee = self.env.ref('advanced_integrate_shopee.s_res_partner_shopee')
                        create_order = dict()
                        order_income = {}
                        if orders_detail.get('order_list'):
                            for rec in orders_detail['order_list']:
                                price_total_items = 0
                                shipping_price = 0
                                phi_bao_hiem = 0
                                try:
                                    note = "Thông tin khách hàng:\nname: %s\nphone: %s\ntown: %s\ndistrict: %s\ncity : %s\nstate : %s\nregion: %s\nzipcode : %s\nfull_address: %s" % (
                                        rec['recipient_address']['name'], rec['recipient_address']['phone'],
                                        rec['recipient_address']['town'], rec['recipient_address']['district'],
                                        rec['recipient_address']['city'], rec['recipient_address']['state'],
                                        rec['recipient_address']['region'], rec['recipient_address']['zipcode'],
                                        rec['recipient_address']['full_address'])
                                    product_orders = []
                                    shipping = self.env['sale.order'].sudo().get_escrow_detail(self.s_shopee_id_order)
                                    shipping_json = shipping.json()
                                    if shipping.status_code == 200:
                                        if shipping_json.get('response'):
                                            response = shipping_json.get('response')
                                            if response.get('order_income'):
                                                order_income = response.get('order_income')
                                                if order_income.get('items'):
                                                    for rec_product in order_income.get('items'):
                                                        list_product, search_product = [], []
                                                        product_uom_qty = rec_product.get('quantity_purchased')
                                                        model_sku = rec_product.get('model_sku') if rec_product.get(
                                                            'model_sku') is not None else ""
                                                        item_sku = rec_product.get('item_sku') if rec_product.get(
                                                            'item_sku') is not None else ""
                                                        search_sku_ky_tu = self.env['product.product'].sudo().search(
                                                            ['|', '&', '&', ('s_mkp_is_sku_ky_tu', '=', True),
                                                             ('s_shopee_to_sync', '=', True),
                                                             ('s_mkp_sku_ky_tu', '=', model_sku), '&', '&',
                                                             ('s_mkp_is_sku_ky_tu', '=', True),
                                                             ('s_shopee_to_sync', '=', True),
                                                             ('s_mkp_sku_ky_tu', '=', item_sku)])
                                                        if search_sku_ky_tu:
                                                            for search_product_product in search_sku_ky_tu:
                                                                search_product.append(search_product_product.id)
                                                                stock_available = search_product_product.stock_quant_ids.filtered(
                                                                    lambda
                                                                        r: r.location_id.warehouse_id and r.quantity > 0 and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True
                                                                           and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).available_quantity
                                                                if stock_available and stock_available > 0:
                                                                    if stock_available >= product_uom_qty and len(
                                                                            list_product) == 0:
                                                                        product = {
                                                                            'product_id': search_product_product.id,
                                                                            'stock_available': product_uom_qty,
                                                                        }
                                                                        list_product.append(product)
                                                                        product_uom_qty = 0
                                                                        break
                                                                    elif (stock_available < product_uom_qty) or len(
                                                                            list_product):
                                                                        if product_uom_qty > 0:
                                                                            if stock_available < product_uom_qty:
                                                                                product = {
                                                                                    'product_id': search_product_product.id,
                                                                                    'stock_available': stock_available
                                                                                }
                                                                                product_uom_qty -= stock_available
                                                                                list_product.append(product)
                                                                            else:
                                                                                product = {
                                                                                    'product_id': search_product_product.id,
                                                                                    'stock_available': product_uom_qty
                                                                                }
                                                                                product_uom_qty = 0
                                                                                list_product.append(product)
                                                                        else:
                                                                            break
                                                            if product_uom_qty != 0:
                                                                created_error = True
                                                                if len(search_product) > 0:
                                                                    context[
                                                                        'message'] = "product: %s không đủ tồn" % rec_product.get(
                                                                        'item_name')
                                                                else:
                                                                    context[
                                                                        'message'] = "product: %s không có trên odoo" % rec_product.get(
                                                                        'item_name')
                                                        else:
                                                            if "," in model_sku or "," in item_sku:
                                                                if model_sku != "":
                                                                    seller_sku = model_sku.split(',')
                                                                elif item_sku != "":
                                                                    seller_sku = item_sku.split(',')
                                                                for r in seller_sku:
                                                                    search_product_product = self.env[
                                                                        'product.product'].sudo().search(
                                                                        ['|', '&', '&', ('s_shopee_to_sync', '=', True),
                                                                         ('default_code', '=',
                                                                          (r.encode('ascii', 'ignore')).decode("utf-8")),
                                                                         ('marketplace_sku', '=', model_sku), '&',
                                                                         ('s_shopee_to_sync', '=', True),
                                                                         ('marketplace_sku', '=', item_sku)])

                                                                    if search_product_product:
                                                                        search_product.append(search_product_product.id)
                                                                        stock_available = search_product_product.stock_quant_ids.filtered(
                                                                            lambda
                                                                                r: r.location_id.warehouse_id and r.quantity > 0 and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True
                                                                                   and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).available_quantity
                                                                        if stock_available and stock_available > 0:
                                                                            if stock_available >= product_uom_qty and len(
                                                                                    list_product) == 0:
                                                                                product = {
                                                                                    'product_id': search_product_product.id,
                                                                                    'stock_available': product_uom_qty,
                                                                                }
                                                                                list_product.append(product)
                                                                                product_uom_qty = 0
                                                                                break
                                                                            elif (stock_available < product_uom_qty) or len(
                                                                                    list_product):
                                                                                if product_uom_qty > 0:
                                                                                    if stock_available < product_uom_qty:
                                                                                        product = {
                                                                                            'product_id': search_product_product.id,
                                                                                            'stock_available': stock_available
                                                                                        }
                                                                                        product_uom_qty -= stock_available
                                                                                        list_product.append(product)
                                                                                    else:
                                                                                        product = {
                                                                                            'product_id': search_product_product.id,
                                                                                            'stock_available': product_uom_qty
                                                                                        }
                                                                                        product_uom_qty = 0
                                                                                        list_product.append(product)
                                                                                else:
                                                                                    break
                                                                if product_uom_qty != 0:
                                                                    created_error = True
                                                                    if len(search_product) > 0:
                                                                        context[
                                                                            'message'] = "product: %s không đủ tồn" % rec_product.get(
                                                                            'item_name')
                                                                    else:
                                                                        context[
                                                                            'message'] = "product: %s không có trên odoo" % rec_product.get(
                                                                            'item_name')
                                                            else:
                                                                search_product_product = self.env[
                                                                    'product.product'].sudo().search(
                                                                    [('default_code', '=', model_sku),
                                                                     ('s_shopee_to_sync', '=',
                                                                      True)]) if model_sku != "" else self.env[
                                                                    'product.product'].sudo().search(
                                                                    [('default_code', '=', item_sku),
                                                                     ('s_shopee_to_sync', '=', True)])
                                                                if search_product_product:
                                                                    stock_available = search_product_product.stock_quant_ids.filtered(
                                                                        lambda
                                                                            r: r.location_id.warehouse_id and r.quantity > 0 and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).available_quantity
                                                                    if stock_available and stock_available >= product_uom_qty:
                                                                        product = {
                                                                            'product_id': search_product_product.id,
                                                                            'stock_available': product_uom_qty,
                                                                        }
                                                                        list_product.append(product)
                                                                    else:
                                                                        created_error = True
                                                                        context[
                                                                            'message'] = "product: %s không đủ tồn" % search_product_product.name
                                                                else:
                                                                    created_error = True
                                                                    context[
                                                                        'message'] = "product: %s không có trên odoo" % rec_product.get(
                                                                        'item_name')
                                                        # if id_product:
                                                        #     product_orders.append(
                                                        #         {
                                                        #             "product_id": id_product,
                                                        #             "product_uom_qty": rec_product.get('quantity_purchased'),
                                                        #             "price_unit": (rec_product.get('discounted_price') if rec_product.get('discounted_price') else rec_product.get('original_price')) / rec_product.get('quantity_purchased')
                                                        #         })
                                                        if list_product:
                                                            for record in list_product:
                                                                product_orders.append(
                                                                    {
                                                                        "product_id": record.get('product_id'),
                                                                        "product_uom_qty": record.get(
                                                                            'stock_available'),
                                                                        "price_unit": (rec_product.get(
                                                                            'discounted_price') if rec_product.get(
                                                                            'discounted_price') else rec_product.get(
                                                                            'original_price')) / rec_product.get(
                                                                            'quantity_purchased')
                                                                    })
                                                else:
                                                    self.env['ir.logging'].sudo().create({
                                                        'name': '#Shopee: get_webhook_order_shopee',
                                                        'type': 'server',
                                                        'dbname': 'boo',
                                                        'level': 'ERROR',
                                                        'path': 'url',
                                                        'message': "items không nằm trong order_income, shipping_json: %s" % str(
                                                            shipping_json),
                                                        'func': 'get_webhook_order_shopee',
                                                        'line': '0',
                                                    })
                                            else:
                                                self.env['ir.logging'].sudo().create({
                                                    'name': '#Shopee: get_webhook_order_shopee',
                                                    'type': 'server',
                                                    'dbname': 'boo',
                                                    'level': 'ERROR',
                                                    'path': 'url',
                                                    'message': "order_income không nằm trong response, shipping_json: %s" % str(
                                                        shipping_json),
                                                    'func': 'get_webhook_order_shopee',
                                                    'line': '0',
                                                })
                                        else:
                                            self.env['ir.logging'].sudo().create({
                                                'name': '#Shopee: get_webhook_order_shopee',
                                                'type': 'server',
                                                'dbname': 'boo',
                                                'level': 'ERROR',
                                                'path': 'url',
                                                'message': "response không nằm trong shipping_json, shipping_json: %s" % str(
                                                    shipping_json),
                                                'func': 'get_webhook_order_shopee',
                                                'line': '0',
                                            })
                                    else:
                                        self.env['ir.config_parameter'].sudo().set_param(
                                            'advanced_integrate_shopee.is_error_token_shopee', 'True')
                                        self.env['ir.logging'].sudo().create({
                                            'name': '#Shopee: recreating_an_error_order_shopee',
                                            'type': 'server',
                                            'dbname': 'boo',
                                            'level': 'ERROR',
                                            'path': 'url',
                                            'message': shipping_json.get('message'),
                                            'func': 'recreating_an_error_order_shopee',
                                            'line': '0',
                                        })
                                        created_error = True
                                        context['message'] = shipping_json.get('message')
                                    if len(product_orders) > 0 and len(product_orders) >= len(
                                            rec['item_list']) and not created_error:
                                        source_id = self.env.ref('advanced_integrate_shopee.utm_source_shopee')
                                        create_order['partner_id'] = customer_shopee.id
                                        create_order['partner_invoice_id'] = customer_shopee.id
                                        create_order['partner_shipping_id'] = customer_shopee.id
                                        create_order['s_shopee_id_order'] = rec['order_sn']
                                        create_order['note'] = note
                                        create_order['s_shopee_is_order'] = True
                                        create_order['marketplace_shopee_order_status'] = rec['order_status']
                                        create_order['warehouse_id'] = self.env['stock.warehouse'].sudo().search(
                                            [('s_shopee_is_mapping_warehouse', '=', True)]).id
                                        create_order['currency_id'] = self.env.company.currency_id.id
                                        create_order['source_id'] = source_id.id
                                        create_order['payment_method'] = "cod" if rec.get('cod') else "online"
                                        carrier_id = False
                                        ####update ngày đặt hàng (create_time)
                                        if rec.get('create_time'):
                                            if len(str(rec.get('create_time'))) == 13:
                                                create_order['date_order'] = datetime.fromtimestamp(
                                                    int(rec.get('create_time')) / 1000)
                                            else:
                                                create_order['date_order'] = datetime.fromtimestamp(
                                                    int(rec.get('create_time')))
                                        order_lines = []
                                        if str(rec['order_status']) in (
                                                'TO_CONFIRM_RECEIVE', 'COMPLETED', 'CANCELLED', 'TO_RETURN'):
                                            create_order['completed_date'] = datetime.fromtimestamp(
                                                int(rec.get('update_time')))
                                        for product_order in product_orders:
                                            order_lines.append((0, 0, {
                                                'product_id': product_order['product_id'],
                                                'product_uom_qty': product_order['product_uom_qty'],
                                                'price_unit': product_order['price_unit'],
                                                'is_product_reward': False
                                            }))

                                        # shipping = self.env['sale.order'].sudo().get_escrow_detail(
                                        #     self.s_shopee_id_order)
                                        # shipping_json = shipping.json()
                                        # if shipping.status_code == 200:
                                        #     if shipping_json.get('response'):
                                        #         response = shipping_json.get('response')
                                        #         if response.get('order_income'):
                                        #             order_income = response.get('order_income')
                                        #             if order_income.get('buyer_paid_shipping_fee'):
                                        #                 shipping_price = abs(
                                        #                     order_income.get('buyer_paid_shipping_fee'))
                                        #                 phi_bao_hiem = abs(order_income.get(
                                        #                     'final_product_protection')) if order_income.get(
                                        #                     'final_product_protection') else 0

                                        # line phi bao hiem shopee
                                        # if phi_bao_hiem:
                                        #     phi_bao_hiem_id, param_phi_bao_hiem = self.env['sale.order'].sudo()._get_shipping_method_shopee("phi bao hiem", phi_bao_hiem)
                                        #     if param_phi_bao_hiem:
                                        #         order_lines.append((0, 0, param_phi_bao_hiem))

                                        # Line discount Shopee
                                        discount_price = order_income.get('voucher_from_seller') if order_income.get(
                                            'voucher_from_seller') >= sum(
                                            [res.get('discount_from_voucher_seller') for res in
                                             order_income.get('items')]) else sum(
                                            [res.get('discount_from_voucher_seller') for res in
                                             order_income.get('items')])
                                        if discount_price > 0:
                                            get_promotion = self.env['sale.order'].sudo()._get_line_discount_shopee(
                                                discount_price)
                                            if get_promotion:
                                                order_lines.append((0, 0, get_promotion))

                                        # Line phí vận chuyển Shopee
                                        # if rec.get('package_list') and len(rec.get('package_list')) > 0:
                                        #     if rec.get('package_list')[0].get('shipping_carrier'):
                                        #         shipping_carrier = rec.get('package_list')[0].get('shipping_carrier')
                                        #         if shipping_carrier and shipping_price and shipping_price > 0:
                                        #             carrier_id, order_line_delivery = self.env[
                                        #                 'sale.order'].sudo()._get_shipping_method_shopee(
                                        #                 shipping_carrier, shipping_price)
                                        #             if order_line_delivery:
                                        #                 order_lines.append((0, 0, order_line_delivery))
                                        if len(order_lines) > 0:
                                            create_order['order_line'] = order_lines
                                        if carrier_id:
                                            create_order['s_carrier_id'] = carrier_id
                                        order = self.env['sale.order'].sudo().create(create_order)
                                        if order:
                                            order.sudo().action_confirm()
                                            if not created_error:
                                                self.return_created = True
                                            ###Sau khi order confirm mới cho write date_order
                                            if create_order.get('date_order'):
                                                order.sudo().write({
                                                    'date_order': create_order.get('date_order')
                                                })
                                            if rec.get('package_list') and len(rec.get('package_list')) > 0:
                                                shopee_package_list = rec.get('package_list')[0]
                                                if order.picking_ids:
                                                    order.picking_ids[0].sudo().write({
                                                        's_shopee_package_number': shopee_package_list.get(
                                                            'package_number')
                                                    })
                                                    # if not order.picking_ids[0].s_shopee_package_number:
                                                    #     if shopee_package_list.get('package_number'):
                                                    #         order.picking_ids[0].s_shopee_package_number = shopee_package_list.get('package_number')
                                                    # if shopee_package_list.get('logistics_status'):
                                                    #     order.picking_ids[0].s_shopee_logistics_status = shopee_package_list.get('logistics_status')
                                            # update order status
                                            if order.marketplace_shopee_order_status in (
                                                    "PROCESSED", "RETRY_SHIP", "SHIPPED", "TO_CONFIRM_RECEIVE",
                                                    "TO_RETURN",
                                                    "COMPLETED"):
                                                picking_ids = order.picking_ids.filtered(
                                                    lambda p: p.state not in ('done', 'cancel'))
                                                if len(order.picking_ids) > 0 and len(picking_ids) > 0:
                                                    for picking in picking_ids:
                                                        if picking.state == 'confirmed':
                                                            picking.action_assign()
                                                        if picking.state == 'assigned':
                                                            picking.action_set_quantities_to_reservation()
                                                            picking.button_validate()
                                            elif order.marketplace_shopee_order_status == "CANCELLED":
                                                for picking in order.picking_ids:
                                                    if picking:
                                                        picking.action_cancel()
                                                order.action_cancel()
                                            if create_order.get('completed_date') and not order.completed_date:
                                                order.sudo().write({
                                                    'completed_date': create_order['completed_date']
                                                })
                                except Exception as e:
                                    created_error = True
                                    context['message'] = str(e)
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': '#Shopee: recreating_an_error_order_shopee',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'path': 'url',
                                'message': "order_list not in orders_detail, orders_detail: %s" % str(orders_detail),
                                'func': 'recreating_an_error_order_shopee',
                                'line': '0',
                            })
            else:
                created_error = True
                context['message'] = api_detail_json.get('message')
        else:
            self.env['ir.config_parameter'].sudo().set_param(
                'advanced_integrate_shopee.is_error_token_shopee', 'True')
            self.env['ir.logging'].sudo().create({
                'name': '#Shopee: recreating_an_error_order_shopee',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': api_detail_json.get('message'),
                'func': 'recreating_an_error_order_shopee',
                'line': '0',
            })
            created_error = True
            context['message'] = api_detail_json.get('message')
        if created_error:
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': context['message'],
                    'type': 'warning',  # types: success,warning,danger,info
                    'sticky': False,  # True/False will display for few seconds if false
                },
            }
            return notification
        elif not created_error and self.return_created:
            rec_unlink = self.sudo().search([('s_shopee_id_order', '=', self.s_shopee_id_order)])
            if rec_unlink:
                rec_unlink.unlink()
            return {
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': '{base_url}/web#view_type=list&model=s.sale.order.error&action={action_sale}'.format(
                    base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                    action_sale=self.env.ref('advanced_integrate_shopee.s_sale_order_shopee_error_act_window').id)
            }

    def _compute_delete_record_recreate_shopee(self):
        for rec in self:
            shopee_order_id = self.env['sale.order'].sudo().search(
                [('s_shopee_id_order', '=', rec.s_shopee_id_order), ('s_shopee_is_order', '=', True)], limit=1)
            if shopee_order_id:
                if rec.level == "ERROR":
                    rec.unlink()
                else:
                    if shopee_order_id.sale_order_status in ['da_giao_hang', 'hoan_thanh', 'huy']:
                        rec.unlink()

    @api.model
    def _cronjob_recreating_order_shopee_error_token(self):
        is_invalid_token = True
        order_queue_ids = self.search([('s_error_token_shopee', '=', True)], limit=50)
        if len(order_queue_ids) > 0:
            for rec in order_queue_ids:
                token_value = self.env['ir.config_parameter'].sudo().get_param(
                    'advanced_integrate_shopee.is_error_token_shopee', '')
                if token_value != 'False':
                    self.env['ir.config_parameter'].sudo().btn_refresh_token_shopee()
                    token_value = self.env['ir.config_parameter'].sudo().get_param(
                        'advanced_integrate_shopee.is_error_token_shopee', '')
                    if token_value == 'False':
                        is_invalid_token = False
                else:
                    is_invalid_token = False
                if not is_invalid_token:
                    shopee_order_id = self.env['sale.order'].sudo().search(
                        [('s_shopee_id_order', '=', rec.s_shopee_id_order), ('s_shopee_is_order', '=', True)], limit=1)
                    if not shopee_order_id:
                        self.env['s.mkp.order.queue'].s_create_order_shopee(rec.s_shopee_id_order)
                        rec.unlink()
