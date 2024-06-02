from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, _logger
import urllib3
import datetime as date
from datetime import datetime, timedelta
from odoo.tests import Form
from collections import Counter
from odoo import http, SUPERUSER_ID
import ast

urllib3.disable_warnings()


class SOrderLazada(models.Model):
    _inherit = "sale.order"

    lazada_order_id = fields.Char("Lazada ID đơn hàng ")
    is_lazada_order = fields.Boolean("Là đơn hàng Lazada")
    marketplace_lazada_order_status = fields.Selection([
        ("unpaid", "Mới"),
        ("pending", "Mới"),
        ("packed", "Đang xử lý"),
        ('repacked', "Đang xử lý"),
        ("ready_to_ship_pending", "Đang xử lý"),
        ("ready_to_ship", "Đang giao hàng"),
        ("shipped", "Hoàn thành"),
        ("delivered", "Hoàn thành"),
        ("returned", "Hoàn thành"),
        ("canceled", "Hủy")
    ], string="Lazada trạng thái đơn hàng")
    shipping_provider_type = fields.Selection([('express', "EXPRESS"),
                                               ("standard", "STANDARD"),
                                               ("economy", "ECONOMY"),
                                               ("instant", "INSTANT"),
                                               ("seller_own_fleet", "SELLER OWN FLEET"),
                                               ("pickup_in_store", "PICKUP IN STORE"),
                                               ("digital", "DIGITAL")
                                               ], string="Lazada phương thức vận chuyển")
    is_return_order_lazada = fields.Boolean(string="Là đơn hoàn trả Lazada")
    reverse_order_id = fields.Char(string="Lazada ID đơn hàng đổi trả")
    return_order_status_lazada = fields.Selection([('new', "Mới"), ('cancelled', "Hủy"),
                                                   ("returned", "Đã nhận hàng"),
                                                   ], string="Lazada trạng thái trả hàng")

    def write(self, vals):
        res = super(SOrderLazada, self).write(vals)
        if vals.get('marketplace_lazada_order_status'):
            self.env.cr.commit()
        return res

    @api.depends('state', 'picking_ids.state', 'marketplace_lazada_order_status')
    def _compute_sale_order_state(self):
        res = super(SOrderLazada, self)._compute_sale_order_state()
        for rec in self:
            if rec.is_lazada_order == True:
                if rec.marketplace_lazada_order_status in ['unpaid', 'pending']:
                    rec.sudo().sale_order_status = 'moi'
                elif rec.marketplace_lazada_order_status in ['packed', 'repacked', 'ready_to_ship_pending']:
                    rec.sudo().sale_order_status = 'dang_xu_ly'
                elif rec.marketplace_lazada_order_status in ['ready_to_ship', 'shipped']:
                    rec.sudo().sale_order_status = 'dang_giao_hang'
                elif rec.marketplace_lazada_order_status in ['delivered', 'returned', 'confirmed']:
                    rec.sudo().sale_order_status = 'hoan_thanh'
                elif rec.marketplace_lazada_order_status == 'canceled':
                    rec.sudo().sale_order_status = 'huy'
        return res

    @api.depends('is_lazada_order')
    def _compute_invisible_context(self):
        for rec in self:
            rec.is_invisible_ecommerce = False
            if rec.is_lazada_order and not rec.is_invisible_ecommerce:
                rec.is_invisible_ecommerce = True

    @api.depends('is_lazada_order')
    def _compute_is_ecommerce_order(self):
        res = super(SOrderLazada, self)._compute_is_ecommerce_order()
        for rec in self:
            if (rec.is_lazada_order or rec.return_order_id.is_lazada_order) and not rec.is_ecommerce_order:
                rec.sudo().write({
                    'is_ecommerce_order': True
                })
        return res

    # Get data of order lazada
    def get_lazada_order(self, order_id):
        api = "/order/get"
        # previous_date = date.datetime.now() - date.timedelta(days=1)
        # next_date = date.datetime.now() + date.timedelta(days=1)
        parameters = {
            "order_id": order_id,
        }
        response = self.env['base.integrate.lazada']._get_data_lazada(api, parameters)
        if response:
            return response['data']

    # Get data product of order lazada
    def get_lazada_order_item(self, order_id):
        api = '/order/items/get'
        parameters = {
            "order_id": order_id
        }
        response = self.env['base.integrate.lazada']._get_data_lazada(api, parameters)
        if response.get('data'):
            return response['data']
        else:
            _logger.error('check /order/items/get')
            _logger.error(response)
            _logger.error('end_check /order/items/get')
            raise ValidationError(response.get('message'))

    def get_voucher_detail(self, promotion_id):
        api = '/promotion/voucher/get'
        parameters = {
            "voucher_type": "COLLECTIBLE_VOUCHER",
            "id": promotion_id
        }
        response = self.env['base.integrate.lazada']._get_data_lazada(api, parameters)
        if response:
            if response['code'] == '0':
                return response['data']

    def get_product_item(self, product_id):
        api = '/product/item/get'
        parameters = {
            'item_id': int(product_id),
        }
        response = self.env['base.integrate.lazada']._get_data_lazada(api, parameters)
        if response:
            if response.get('code') == '0':
                return response.get('data')

    def sync_order_lazada(self, data):
        try:
            if data.get('data'):
                order_id = data['data'].get('trade_order_id')
                order_status = data['data'].get('order_status')
                timestamp = data['timestamp']
                # if order_id not in self.search([("is_lazada_order", '=', True)]).mapped("lazada_order_id"):
                order_items = self.get_lazada_order_item(order_id)
                if order_items:
                    warehouse_id = self.env["stock.warehouse"].sudo().search([("is_push_lazada", '=', True)], limit=1)
                    if not warehouse_id:
                        raise ValidationError('Chưa đồng bộ kho hàng Lazada')
                    date_order = False
                    if timestamp:
                        date_order = datetime.fromtimestamp(int(timestamp)) - date.timedelta(hours=7)
                    customer_lazada = self.env.ref('advanced_integrate_lazada.customer_lazada')
                    source_id = self.env.ref('advanced_integrate_lazada.utm_source_lazada')
                    if self.env.ref('product.list0'):
                        pricelist_id = self.env.ref('product.list0')
                    else:
                        pricelist_id = self.env.sudo().search([], limit=1)
                    if customer_lazada:
                        # Phương thức thanh toán
                        payment_method = 'online'
                        order_item = self.get_lazada_order(order_id)
                        if order_item:
                            if order_item.get('payment_method') == 'COD':
                                payment_method = 'cod'

                        values = {
                            "partner_id": customer_lazada.id,
                            "pricelist_id": pricelist_id.id if pricelist_id else False,
                            "partner_invoice_id": customer_lazada.id,
                            "partner_shipping_id": customer_lazada.id,
                            "lazada_order_id": order_id,
                            "is_lazada_order": True,
                            "marketplace_lazada_order_status": order_status,
                            "warehouse_id": warehouse_id.id,
                            "currency_id": pricelist_id.currency_id.id if pricelist_id else None,
                            "date_order": date_order,
                            "shipping_provider_type": order_items[0]["shipping_provider_type"],
                            "source_id": source_id.id if source_id else False,
                            'payment_method': payment_method
                        }
                        order_item_ids = []
                        order_line_ids = []
                        list_product_lazada = []
                        shipping_fee = 0
                        shipping_fee_discount = 0
                        list_promo = []
                        promotion_seller_code = None
                        promtion_lazada_code = None
                        voucher_seller = None
                        voucher_platform = 0
                        lazada_merged_order_line = {}
                        product_sku = None
                        for item in order_items:
                            promotion_seller_code = item.get('voucher_code_seller')
                            promtion_lazada_code = item.get('voucher_code_platform')
                            voucher_seller = item.get('voucher_seller')
                            if promotion_seller_code:
                                list_promo.append(str(item['voucher_code_seller']))
                            if promtion_lazada_code:
                                list_promo.append(str(item['voucher_code_platform']))
                            voucher_platform += item['voucher_platform']
                            shipping_fee += item['shipping_fee_original']
                            shipping_fee_discount += (item['shipping_fee_discount_platform'] + item[
                                'shipping_fee_discount_seller'])
                            # Lấy sku hiện tại của sản phẩm trên Lazada
                            if item.get('product_id'):
                                skus = self.get_product_item(product_id=item.get('product_id'))
                                if skus.get('skus'):
                                    for sku in skus.get('skus'):
                                        if str(sku.get('SkuId')) == item.get('sku_id'):
                                            item['sku'] = sku.get('SellerSku')
                                            break
                            if lazada_merged_order_line.get(item['sku']):
                                lazada_merged_order_line[item['sku']]['product_uom_qty'] += 1
                            else:
                                lazada_merged_order_line[item['sku']] = {'product_uom_qty': 1,
                                                                         'price_unit': item['item_price']}
                        if list_promo:
                            values['s_promo_code'] = ",".join(set(list_promo)) if len(list_promo) > 0 else False
                        for key, val in lazada_merged_order_line.items():
                            # search product MKP
                            product_ids = self.env['product.product'].sudo().search(
                                ['&', ('to_sync_lazada', '=', True),
                                 '|', ('default_code', '=', key),
                                 '&', ('marketplace_sku', '=', key), ('is_merge_product', '=', True)])
                            if len(product_ids) > 0:
                                # san pham duoc merge
                                marketplace_sku = product_ids.filtered(lambda p: p.is_merge_product)
                                if len(marketplace_sku) > 0:
                                    lazada_product_sku_ids = marketplace_sku[0].marketplace_sku.split(',')
                                else:
                                    lazada_product_sku_ids = [product_ids[0].default_code]
                                if len(lazada_product_sku_ids) > 0:
                                    remaining_qty = val['product_uom_qty']
                                    for product in lazada_product_sku_ids:
                                        product_id = product_ids.filtered(lambda p: p.default_code == product)
                                        check_available_quantity = product_id.stock_quant_ids.filtered(
                                            lambda
                                                r: r.location_id.warehouse_id.e_commerce == 'lazada' and r.location_id.warehouse_id.is_push_lazada == True)
                                        # if len(check_available_quantity) == 0:
                                        #     raise ValidationError('Sản phẩm %s không đủ tồn kho' % str(lazada_product_sku_ids))
                                        # else:
                                        if check_available_quantity:
                                            available_quantity = check_available_quantity[0].available_quantity
                                            if available_quantity > 0:
                                                # lay so luong order line, so sanh kho cua cac san pham merged
                                                if remaining_qty >= available_quantity:
                                                    remaining_qty -= available_quantity
                                                    order_line_ids.append((0, 0, {
                                                        "product_id": product_id.id,
                                                        "product_uom_qty": available_quantity,
                                                        'price_unit': val['price_unit']
                                                    }))
                                                    list_product_lazada.append(product_id.id)
                                                else:
                                                    order_line_ids.append((0, 0, {
                                                        "product_id": product_id.id,
                                                        "product_uom_qty": remaining_qty,
                                                        'price_unit': val['price_unit']
                                                    }))
                                                    remaining_qty -= remaining_qty
                                                    list_product_lazada.append(product_id.id)
                                                    break
                                    if remaining_qty > 0:
                                        raise ValidationError('Sản phẩm %s không đủ tồn kho' % str(lazada_product_sku_ids))
                            else:
                                raise ValidationError('Sản phẩm %s không tồn tại' % str(key))
                        # Thêm line phí vận chuyển
                        # shipping_fee = float(shipping_fee) - float(shipping_fee_discount)
                        # if shipping_fee:
                        #     product_shipping_fee = self.env['product.product'].search(
                        #         [('is_shipping_fee_lazada', '=', True)])
                        #     if not product_shipping_fee:
                        #         product_shipping_fee = self.env['product.product'].sudo().create({
                        #             'name': "Phí vận chuyển",
                        #             'detailed_type': 'service',
                        #             'lst_price': float(shipping_fee) - float(
                        #                 shipping_fee_discount) if shipping_fee else 0,
                        #             'is_shipping_fee_lazada': True
                        #         })
                        #     if product_shipping_fee:
                        #         order_line_ids.append((0, 0, {
                        #             "product_id": product_shipping_fee.id,
                        #             "price_unit": float(shipping_fee) - float(shipping_fee_discount),
                        #             "is_delivery": True
                        #         }))
                        # Thêm line chương trình khuyến mãi nhà bán
                        if promotion_seller_code is not "" or voucher_seller != 0:
                            lst_price = 0
                            for item in order_items:
                                if item.get('voucher_seller'):
                                    lst_price += float(item.get('voucher_seller'))
                            voucher_seller_details = self.get_voucher_detail(promotion_seller_code)
                            if voucher_seller_details is None:
                                voucher_seller_details = {
                                    'voucher_name': 'Seller Discount Total'
                                }
                            product_promo_seller_id = self.env['product.product'].search([
                                ('name', '=', voucher_seller_details['voucher_name']),
                                ('is_promo_seller_lazada', '=', True)])
                            if product_promo_seller_id:
                                product_promo_seller_id.write({
                                    "lst_price": -lst_price
                                })
                            else:
                                product_promo_seller_id = self.env['product.product'].sudo().create({
                                    'name': voucher_seller_details['voucher_name'],
                                    'detailed_type': 'service',
                                    'lst_price': -lst_price,
                                    'is_promo_lazada': True
                                })
                            order_line_ids.append((0, 0, {
                                "product_id": product_promo_seller_id.id,
                                "is_line_coupon_program": True,
                                "is_ecommerce_reward_line": True
                            }))
                        # Line chương trình khuyến mãi Lazada
                        # if promtion_lazada_code is not "":
                        #     if order_items[0].get('voucher_platform'):
                        #         product_promo_lazada_id = self.env['product.product'].search(
                        #             [('is_promo_lazada', '=', True)])
                        #         if product_promo_lazada_id:
                        #             product_promo_lazada_id.write(
                        #                 {"lst_price": -float(voucher_platform)})
                        #         else:
                        #             product_promo_lazada_id = self.env['product.product'].sudo().create({
                        #                 'name': "Chương trình khuyến mại Lazada " + promtion_lazada_code,
                        #                 'detailed_type': 'service',
                        #                 'lst_price': -float(voucher_platform) if
                        #                 order_items['voucher_platform'] else 0,
                        #                 'is_promo_lazada': True
                        #             })
                        #         if product_promo_lazada_id:
                        #             order_line_ids.append((0, 0, {
                        #                 "product_id": product_promo_lazada_id.id,
                        #                 "is_line_coupon_program": True,
                        #                 "is_ecommerce_reward_line": True
                        #             }))

                        if len(order_line_ids) > 0 and len(list_product_lazada) > 0:
                            values['order_line'] = order_line_ids
                            order = self.create(values)
                            if order:
                                order.action_confirm()
                                if order_items[0].get('created_at'):
                                    create_date = datetime.strptime(order_items[0].get('created_at').replace(' +0700', ''),'%Y-%m-%d %H:%M:%S')
                                    order.sudo().write({
                                        'date_order': create_date - timedelta(hours=7)
                                    })
                                if order.picking_ids:
                                    if order.marketplace_lazada_order_status not in ['unpaid', 'pending']:
                                        for picking_id in order.picking_ids:
                                            if not picking_id.is_do_lazada_return and picking_id.state not in ['done']:
                                                picking_id.sudo().action_set_quantities_to_reservation()
                                                picking_id.sudo().button_validate()
                                    # cancel DO
                                    if order.marketplace_lazada_order_status in ['canceled', 'returned']:
                                        for picking_id in order.picking_ids:
                                            if picking_id.state not in ['done']:
                                                order.with_context({'disable_cancel_warning': True}).action_cancel()
                                list_product_lazada.clear()
                                return order
                        else:
                            raise ValidationError('Sản phẩm không tồn tại')
        except Exception as e:
            self.env['s.lazada.queue'].sudo().create({
                'dbname': 'boo',
                'level': 'status_error',
                'message': str(e),
                's_lazada_id_order': data.get('data').get('trade_order_id'),
                'order_status': data.get('data').get('order_status'),
                'data': data
            })

    def get_lazada_shipment_providers(self, order_id, order_item_ids):
        api = '/order/shipment/providers/get'
        parameters = {
            "getShipmentProvidersReq": {

                "orders": [
                    {"order_id": order_id, "order_item_ids": order_item_ids}]
            }
        }
        response = self.env['base.integrate.lazada']._post_data_lazada(api, parameters)
        if response:
            if 'result' in response:
                return response['result']['data']

    def set_lazada_order_packed(self, order_id, order_item_ids, shipping_allocate_type):
        api = '/order/fulfill/pack'
        parameters = {
            "packReq": {

                "pack_order_list": [{
                    "order_item_list": order_item_ids, "order_id": order_id}],
                "delivery_type": "dropship", "shipping_allocate_type": shipping_allocate_type
            }
        }
        response = self.env['base.integrate.lazada']._post_data_lazada(api, parameters)
        if response:
            if 'result' in response:
                return response['result']['data']

    def set_lazada_order_ready_to_ship(self, package_id):
        api = "/order/package/rts"
        parameters = {
            "readyToShipReq": {
                "packages": [{"package_id": package_id}]
            }
        }
        response = self.env['base.integrate.lazada']._post_data_lazada(api, parameters)
        if response:
            if 'result' in response:
                return response['result']['data']

    def set_lazada_order(self, order, order_item_ids):
        shipping_allocate_type = self.get_lazada_shipment_providers(order.lazada_order_id, order_item_ids)
        if shipping_allocate_type and order.marketplace_lazada_order_status == 'pending':
            package_id = self.set_lazada_order_packed(order.lazada_order_id, order_item_ids,
                                                      shipping_allocate_type['shipping_allocate_type'])
            if package_id:
                order.write({
                    "marketplace_lazada_order_status": 'packed'
                })
                # res = self.set_lazada_order_ready_to_ship(
                #     package_id['pack_order_list'][0]['order_item_list'][0]['package_id'])
                # if 'packages' in res:
                #     order.write({
                #         "marketplace_lazada_order_status": 'ready_to_ship'
                #     })
                #     order.picking_ids[0].write({
                #         "picking_lazada_status": "ready_to_ship"
                #     })

    def _compute_return_stock_picking_lazada(self, order_id):
        self.env.uid = SUPERUSER_ID
        for picking_id in order_id.picking_ids:
            if not picking_id.is_do_lazada_return:
                return_picking_old_id = order_id.picking_ids.filtered(lambda p: picking_id.name in p.origin)
                if return_picking_old_id:
                    break
                return_picking_id = self.env['stock.return.picking'].sudo().create(
                    {'picking_id': picking_id.id})
                # Them san pham vao return DO
                return_picking_id.sudo()._onchange_picking_id()
                # Tao DO return
                if len(return_picking_id.product_return_moves) > 0 and sum(
                        return_picking_id.product_return_moves.mapped('quantity')) > 0:
                    result_return_picking = return_picking_id.sudo().create_returns()
                    if result_return_picking:
                        do_return = self.env['stock.picking'].sudo().search(
                            [('id', '=', result_return_picking.get('res_id'))])
                        do_return.write({'is_do_lazada_return': True})

    def create_return_sale_order_lazada(self, order_id, data):
        so_lines = []
        product_uom_qty = 1
        for reverse_line in data.get('reverseOrderLineDTOList'):
            sku = reverse_line.get('seller_sku_id')
            if sku:
                order_line_id = order_id.order_line.filtered(lambda line: line.product_id.default_code == sku or (
                    sku in line.product_id.marketplace_sku.split(
                        ',') if line.product_id.marketplace_sku != False else False))
                if order_line_id:
                    is_insert_order_line = True
                    if len(so_lines) > 0:
                        for item in so_lines:
                            if item[2]['product_id'] == order_line_id[0].product_id.id:
                                item[2]['product_uom_qty'] -= 1
                                item[2]['lazada_reverse_status'] = reverse_line.get('reverse_status')
                                is_insert_order_line = False
                    if is_insert_order_line:
                        so_lines.append((0, 0, {
                            'product_id': order_line_id[0].product_id.id,
                            'name': order_line_id[0].name,
                            'product_uom_qty': float(-product_uom_qty),
                            'product_uom': order_line_id[0].product_uom.id,
                            'price_unit': order_line_id[0].price_unit,
                            'refunded_orderline_id': order_line_id[0].id,
                            'gift_card_id': order_line_id[0].gift_card_id.id if order_line_id[
                                0].gift_card_id else False,
                            'coupon_program_id': order_line_id[0].coupon_program_id.id if order_line_id[
                                0].coupon_program_id else False,
                            'tax_id': [(6, 0, order_line_id[0].tax_id.ids)] if order_line_id[
                                0].tax_id else False,
                            'is_line_coupon_program': order_line_id[0].is_line_coupon_program,
                            'is_ecommerce_reward_line': order_line_id[0].is_ecommerce_reward_line,
                            'is_delivery': order_line_id[0].is_delivery,
                            'is_loyalty_reward_line': order_line_id[0].is_loyalty_reward_line,
                            's_loyalty_point_lines': order_line_id[0].s_loyalty_point_lines,
                            's_redeem_amount': order_line_id[0].s_redeem_amount,
                        }))
        if len(so_lines) > 0:
            # Return CTKM
            promotion_seller_id = order_id.order_line.filtered(lambda line: line.product_id.detailed_type == 'service')
            if promotion_seller_id:
                for promotion in promotion_seller_id:
                    so_lines.append((0, 0, {
                        'product_id': promotion[0].product_id.id,
                        'name': promotion[0].name,
                        'product_uom_qty': -1,
                        'product_uom': promotion[0].product_uom.id,
                        'price_unit': promotion[0].price_unit,
                        'refunded_orderline_id': promotion[0].id,
                        'gift_card_id': promotion[0].gift_card_id.id if promotion[
                            0].gift_card_id else False,
                        'coupon_program_id': promotion[0].coupon_program_id.id if promotion[
                            0].coupon_program_id else False,
                        'tax_id': [(6, 0, promotion[0].tax_id.ids)] if promotion[
                            0].tax_id else False,
                        'is_line_coupon_program': promotion[0].is_line_coupon_program,
                        'is_ecommerce_reward_line': promotion[0].is_ecommerce_reward_line,
                        'is_delivery': promotion[0].is_delivery,
                        'is_loyalty_reward_line': promotion[0].is_loyalty_reward_line,
                        's_loyalty_point_lines': promotion[0].s_loyalty_point_lines,
                        's_redeem_amount': promotion[0].s_redeem_amount,
                    }))
            sale_order = {
                'partner_id': order_id.partner_id.id if order_id.partner_id else False,
                'return_order_id': order_id.id,
                'payment_method': order_id.payment_method if order_id.payment_method else False,
                'order_line': so_lines,
                'is_return_order': True,
                'lazada_order_id': order_id.lazada_order_id,
                'reverse_order_id': str(data.get('reverse_order_id')),
                'source_id': order_id.source_id.id if order_id.source_id else False,
                'is_return_order_lazada': True,
                'warehouse_id': order_id.warehouse_id.id,
                'is_lazada_order': True,
            }
            sale_order_id = self.sudo().create(sale_order)
            if sale_order_id:
                sale_order_id.sudo().write({'sale_order_status': 'dang_xu_ly'})
                amount_untaxed = 0
                amount_tax = 0
                for line in sale_order_id.order_line:
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
                amount_total = amount_untaxed + amount_tax
                sale_order_id.update({
                    'name': sale_order_id.name + ' - Đổi trả đơn ' + order_id.name,
                    'amount_untaxed': amount_untaxed,
                    'amount_tax': amount_tax,
                    'amount_total': amount_total
                })
                sale_order_id.sudo().action_confirm()
                return sale_order_id

    def create_so_return(self, data, order_id):
        self.env.uid = SUPERUSER_ID
        response = self.get_order_reverse_return_detail(data)
        if response.get('data'):
            sale_order_return = self.create_return_sale_order_lazada(order_id, response.get('data'))
            return sale_order_return

    def get_order_reverse_return_detail(self, data):
        self.env.uid = SUPERUSER_ID
        api = '/order/reverse/return/detail/list'
        reverse_order_id = data.get('data').get('reverse_order_id')
        if reverse_order_id:
            parameters = {
                'reverse_order_id': reverse_order_id
            }
            response = self.env['base.integrate.lazada']._get_data_lazada(api, parameters)
            return response

    def build_order_lazada(self, order_id, data):
        try:
            status_origin = order_id.marketplace_lazada_order_status
            # Status Lazada order
            order_status = data.get('data').get('order_status')
            # order_id.write({'marketplace_lazada_order_status': order_status})
            # Write order status
            if order_id.marketplace_lazada_order_status in ['unpaid']:
                order_id.write({'marketplace_lazada_order_status': order_status})
            elif (order_id.marketplace_lazada_order_status == 'pending' and
                  order_status in ['packed', 'repacked', 'ready_to_ship_pending',
                                   'ready_to_ship', 'shipped', 'delivered', 'canceled']):
                order_id.write({'marketplace_lazada_order_status': order_status})
            elif (order_id.marketplace_lazada_order_status == 'packed' and
                  order_status in ['ready_to_ship_pending', 'ready_to_ship', 'shipped', 'delivered',
                                   'canceled']):
                order_id.write({'marketplace_lazada_order_status': order_status})
            elif order_id.marketplace_lazada_order_status == 'ready_to_ship_pending' and order_status in [
                'ready_to_ship', 'shipped', 'delivered', 'canceled']:
                order_id.write({'marketplace_lazada_order_status': order_status})
            elif (order_id.marketplace_lazada_order_status == 'ready_to_ship' and
                  order_status in ['shipped', 'delivered', 'canceled']):
                order_id.write({'marketplace_lazada_order_status': order_status})
            elif order_id.marketplace_lazada_order_status == 'shipped' and order_status in [
                'delivered']:
                order_id.write({'marketplace_lazada_order_status': order_status})
            # Write order status
            if not order_id.is_return_order_lazada:
                # get package_id
                if len(order_id.picking_ids) > 0:
                    if not order_id.picking_ids[0].package_lazada_id:
                        order_lazada = self.sudo().get_lazada_order_item(
                            data['data']['trade_order_id'])
                        package_id = order_lazada[0].get('package_id')
                        if len(package_id) > 0:
                            order_id.picking_ids[0].package_lazada_id = package_id
                # auto confirm DO in Odoo
                if order_status in ['packed', 'repacked', 'ready_to_ship_pending', 'ready_to_ship',
                                    'shipped',
                                    'delivered'] and order_id.picking_ids.state != 'done':
                    order_id.picking_ids.sudo().action_set_quantities_to_reservation()
                    order_id.picking_ids.sudo().button_validate()
                if order_status in ['delivered']:
                    if not order_id.completed_date and data.get('timestamp'):
                        order_id.completed_date = datetime.fromtimestamp(
                            data.get('timestamp'))
                if order_status == 'canceled' and order_id.sale_order_status not in ['hoan_thanh',
                                                                                     'hoan_thanh_1_phan']:
                    if order_id.picking_ids.state != 'done':
                        # Cancel DO
                        order_id.picking_ids.sudo().action_cancel()
                    else:
                        # Return DO
                        self.sudo()._compute_return_stock_picking_lazada(
                            order_id=order_id)
                    order_id.completed_date = datetime.fromtimestamp(
                        data.get('timestamp'))
            # Chi hoan tien
            if data.get('data').get('reverse_order_id'):
                if order_status == 'delivered':
                    sale_order_return = self.sudo().search(
                        [('reverse_order_id', '=', str(data.get('data').get('reverse_order_id')))],
                        limit=1)
                    if not len(sale_order_return) > 0:
                        so_return = self.create_so_return(data, order_id)
                    else:
                        is_returned = False
                        order_reverse_details = self.get_order_reverse_return_detail(data)
                        if order_reverse_details.get('data'):
                            data = order_reverse_details.get('data')
                            if data.get('reverseOrderLineDTOList'):
                                for line in data.get('reverseOrderLineDTOList'):
                                    if line.get('reverse_status') in ['CANCEL_SUCCESS',
                                                                      'CANCEL_REFUND_ISSUED',
                                                                      'RTM_CANCELED', 'RTW_CANCELED',
                                                                      'REFUND_SUCCESS',
                                                                      'REFUND_REJECTED']:
                                        is_returned = True
                                    else:
                                        is_returned = False
                        if is_returned:
                            sale_order_return.write({'return_order_status_lazada': 'returned'})
            else:
                pass
        except Exception as e:
            self.env['s.lazada.queue'].sudo().create({
                'dbname': 'boo',
                'level': 'status_error',
                'message': str(e),
                's_lazada_id_order': data.get('data').get('trade_order_id'),
                'order_status': data.get('data').get('order_status'),
                'data': data
            })

    def _cron_compute_line_shipping_free_lazada(self):
        sale_order_lazada_ids = self.search([('is_lazada_order', '=', True)])
        if sale_order_lazada_ids:
            for sale_order_lazada_id in sale_order_lazada_ids:
                if sale_order_lazada_id.order_line:
                    for order_line_lazada in sale_order_lazada_id.order_line:
                        if order_line_lazada.name == 'Phí vận chuyển':
                            order_line_lazada.is_delivery = True

    def get_ovo_orders(self, order_id):
        api = "/orders/ovo/get"
        parameters = {
            "tradeOrderIds": order_id,
        }
        response = self.env['base.integrate.lazada']._get_data_lazada(api, parameters)
        if response:
            return response['result']

    def compute_completed_date(self):
        order_ids = self.sudo().search(
            [('is_lazada_order', '=', True), ('sale_order_status', 'in', ['hoan_thanh', 'huy'])])
        if len(order_ids) > 0:
            for order_id in order_ids:
                order_item = self.get_ovo_orders(order_id=order_id.lazada_order_id)
                if order_item:
                    if len(order_item.get('tradeOrders')) > 0:
                        if order_item.get('tradeOrders')[0].get('tradeOrderLines')[0].get('deliveredTime'):
                            delivered_time = order_item.get('tradeOrders')[0].get('tradeOrderLines')[0].get(
                                'deliveredTime')
                            completed_date = (datetime.strptime(delivered_time.replace('+07:00[GMT+07:00]', ''),
                                                                '%Y-%m-%dT%H:%M:%S.%f') - timedelta(hours=7)).replace(
                                microsecond=0)
                            self._cr.execute("""
                                UPDATE sale_order
                                SET completed_date=%s
                                WHERE id=%s
                            """, (completed_date, order_id.id))


class SSaleOrderError(models.Model):
    _name = "s.sale.order.lazada.error"
    _order = 'create_date desc'

    dbname = fields.Char()
    level = fields.Char()
    message = fields.Char()
    return_created = fields.Boolean(default=False, string="Đã tạo lại đơn")
    order_status = fields.Char()
    s_lazada_id_order = fields.Char(string="Id Lazada")
    data = fields.Char()

    def recreating_an_error_order_lazada(self):
        try:
            lazada_order_id = self.env['sale.order'].sudo().search([('lazada_order_id', '=', self.s_lazada_id_order)], limit=1)
            if len(lazada_order_id) > 0:
                self.env['sale.order'].sudo().build_order_lazada(lazada_order_id, ast.literal_eval(self.data))
            else:
                lazada_order_id = self.env['sale.order'].sudo().sync_order_lazada(ast.literal_eval(self.data))
            if lazada_order_id:
                self.sudo().search([('s_lazada_id_order', '=', lazada_order_id.lazada_order_id)], limit=1).unlink()
                return {
                    'name': _("Đơn hàng Lazada bị lỗi"),
                    'view_mode': 'tree',
                    'res_model': 's.sale.order.lazada.error',
                    'type': 'ir.actions.act_window',
                    'view_id': self.env.ref('advanced_integrate_lazada.s_sale_order_lazada_error_view_tree').id,
                    'target': 'current',
                    'context': {'create': False, 'edit': False, 'delete': False}
                }
        except Exception as e:
            _logger.error(e.args)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': str(e),
                    'type': 'warning',  # types: success,warning,danger,info
                    'sticky': False,  # True/False will display for few seconds if false
                },
            }


