from odoo import models, fields, api, _
import json
from odoo.exceptions import ValidationError, _logger
from odoo.tests import Form
import datetime, time
from datetime import date, timedelta, datetime
from ..tools.api_wrapper_tiktok import validate_integrate_token


class SSaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    tiktok_order_id = fields.Char("ID đơn hàng Tiktok", readonly=True)
    is_tiktok_order = fields.Boolean("Là Đơn Hàng Tiktok", readonly=True)
    marketplace_tiktok_order_status = fields.Selection([("100", "UNPAID"),
                                                        ("111", "AWAITING_SHIPMENT"),
                                                        ("112", "AWAITING_COLLECTION"),
                                                        ("114", "PARTIALLY_SHIPPING"),
                                                        ("121", "IN_TRANSIT"),
                                                        ("122", "DELIVERED"),
                                                        ("130", "COMPLETED"),
                                                        ("140", "CANCELLED")], string="Tình trạng đơn hàng Tiktok",
                                                       default=False)
    s_tiktok_payment_method = fields.Selection(
        [("1", "BANK_TRANSFER"), ("2", "CASH"), ("3", "DANA_WALLET"), ("4", "BANK_CARD"),
         ("5", "OVO"), ("6", "CASH_ON_DELIVERY"), ("7", "GO_PAY"), ("8", "PAYPAL"),
         ("9", "APPLEPAY"), ("10", "SHOPEEPAY"), ("11", "KLARNA"),
         ("12", "KLARNA_PAY_NOW"),
         ("13", "KLARNA_PAY_LATER"), ("14", "KLARNA_PAY_OVER_TIME"), ("15", "TRUE_MONEY"),
         ("16", "RABBIT_LINE_PAY"), ("17", "IBANKING"), ("18", "TOUCH_GO"),
         ("19", "BOOST"), ("0", ""),
         ("20", "ZALO_PAY"), ("21", "MOMO"), ("22", "BLIK"), ("23", "PAYMAYA"),
         ("24", "GCASH"), ("25", "AKULAKU"), ("26", "GOOGLE_PAY"), ("27", "GRAB_PAY"),
         ("28", "Domestic ATM Card")], string="Payment Method", readonly=True)
    s_tiktok_status_return = fields.Selection(
        [("4", "Đang xử lý"), ("99", "Trả hàng thất bại"), ("100", "Trả hàng thành công")],
        string="Trạng thái trả hàng")
    is_return_order_tiktok = fields.Boolean(string="Là đơn đổi trả Tiktok")
    # source_ecommerce = fields.Char(string="Nguồn", compute="_compute_source_ecommerce", store=True)
    tiktok_reverse_order_id = fields.Char(string="Id trả hàng Tiktok")
    reverse_event_type = fields.Char()
    refund_total_tiktok = fields.Float()
    is_tiktok_customer_canceled = fields.Boolean(string="Là đơn Tiktok đã hủy bởi khách hàng")

    @api.depends('is_tiktok_order')
    def _compute_invisible_context(self):
        for rec in self:
            rec.is_invisible_ecommerce = False
            if rec.is_tiktok_order and not rec.is_invisible_ecommerce:
                rec.is_invisible_ecommerce = True

    @api.depends('is_tiktok_order')
    def _compute_is_ecommerce_order(self):
        res = super(SSaleOrderInherit, self)._compute_is_ecommerce_order()
        for rec in self:
            if (rec.is_tiktok_order or rec.return_order_id.is_tiktok_order) and not rec.is_ecommerce_order:
                rec.sudo().write({
                    'is_ecommerce_order': True
                })
        return res

    @api.depends('state', 'picking_ids.state', 'marketplace_tiktok_order_status', 'picking_ids.package_status')
    def _compute_sale_order_state(self):
        res = super(SSaleOrderInherit, self)._compute_sale_order_state()
        for rec in self:
            if rec.is_tiktok_order == True:
                if rec.marketplace_tiktok_order_status in ['100', '111']:
                    rec.sudo().sale_order_status = 'moi'
                elif rec.marketplace_tiktok_order_status == '112':
                    rec.sudo().sale_order_status = 'dang_xu_ly'
                elif rec.marketplace_tiktok_order_status == '121':
                    rec.sudo().sale_order_status = 'dang_giao_hang'
                elif rec.marketplace_tiktok_order_status == '130' and rec.sudo().sale_order_status not in [
                    'hoan_thanh_1_phan', 'huy', 'giao_hang_that_bai']:
                    rec.sudo().sale_order_status = 'hoan_thanh'
                elif rec.marketplace_tiktok_order_status == "122":
                    rec.sudo().sale_order_status = 'hoan_thanh'
                elif rec.marketplace_tiktok_order_status == '140':
                    rec.sudo().sale_order_status = 'huy'
        return res

    # @api.depends('is_tiktok_order', 'is_lazada_order')
    # def _compute_source_ecommerce(self):
    #     for r in self:
    #         r.sudo().source_ecommerce = False
    #         if r.is_tiktok_order:
    #             r.sudo().source_ecommerce = "Tiktok"
    #         elif r.is_magento_order:
    #             r.sudo().source_ecommerce = "Magento"
    #         elif r.is_lazada_order:
    #             r.sudo().source_ecommerce = "Lazada"

    # @validate_integrate_token
    def get_order(self, cursors=None, param=None):
        if param is None:
            param = {}
        url_api = '/api/orders/search'
        payload = {
            "page_size": 20
        }
        payload.update(param)
        if cursors:
            payload.update({"cursor": cursors})
        req = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload)).json()
        if req['code'] == 0:
            id_order_list = []
            if 'order_list' in req['data']:
                for r in req['data']['order_list']:
                    id_order_list.append(r['order_id'])
                return req['data'], id_order_list
            else:
                return req['data'], False

    # @validate_integrate_token
    def get_order_details(self, id_order_list):
        url_api = "/api/orders/detail/query"
        payload = {
            "order_id_list": [id_order_list]
        }
        response = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload)).json()
        if response['code'] == 0:
            return response['data']
        else:
            self.env['s.sale.order.error'].sudo().create({
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(response.get('message')) if response.get('message') else 'Không có message trả về',
                'tiktok_order_id': id_order_list,
                'order_status': '',
            })
            return None

    def btn_infor_customer(self):
        view = self.env.ref('advanced_integrate_tiktok.infor_customer_type_form_view')
        return {
            'name': _('Cập nhật'),
            'type': 'ir.actions.act_window',
            'res_model': 'mass.action.infor.customer',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {'default_s_order_id': self.id}
        }

    ###Start test create/update/get promotion
    # @validate_integrate_token
    def _add_promotion_details(self):
        url_api = "/api/promotion/activity/create"
        payload = {
            'request_serial_no': 'create202208291503530001100220053',
            'title': 'DiscountEvent0840',
            'promotion_type': 1,
            'begin_time': 1961756830,
            'end_time': 1961856830,
            'product_type': 2
        }
        req = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload)).json()
        if req['code'] == 0:
            return req['data'].get('promotion_id')

    def _get_line_discount_tiktok(self, discount_price=False):
        order_line = False
        if discount_price:
            product_coupon_program = self.env.ref('advanced_integrate_tiktok.s_line_discount_tiktok')
            if product_coupon_program:
                product_coupon_program.write({
                    # 'lst_price': float(discount_price) if discount_price else 0,
                    'name': 'Promo Discount Tiktok: ' + str(discount_price) if discount_price else str(
                        product_coupon_program.display_name),
                })
                order_line = {
                    "product_id": product_coupon_program.id,
                    "product_uom_qty": 1,
                    "price_unit": -float(discount_price) if discount_price else 0,
                    "s_lst_price": 0,
                    "is_line_coupon_program": True,
                    "is_ecommerce_reward_line": True,
                }
        return order_line

    ### start Get reverse order tiktok
    # @validate_integrate_token
    def _get_reverse_order_list(self, reverse_order_id):
        url_api = "/api/reverse/reverse_order/list"
        payload = {
            "offset": 0,
            "size": 20,
            "reverse_order_id": reverse_order_id
        }
        req = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload)).json()
        if req.get('code') == 0:
            return req.get('data')

    ### end reverse order tiktok

    def _amount_all(self):
        res = super(SSaleOrderInherit, self)._amount_all()
        for order in self:
            if order.is_return_order_tiktok and not order.amount_total:
                order.amount_total = sum(order.order_line.mapped('price_total'))
        return res

    ### start create refund only sale order tiktok
    def create_refund_only_sale_order_tiktok(self, reverse_list, order_id, status):
        try:
            ### start test return and refund = postman
            if reverse_list.get('reverse_event_type') == "testreturn":
                reverse_list = {
                    "refund_total": reverse_list.get('refund_total'),
                    "return_item_list": reverse_list['return_item_list']

                }
            ### end test return and refund = postman
            order = self.env['sale.order'].sudo().search([('tiktok_order_id', '=', order_id)], limit=1)
            warehouse = self.env['stock.warehouse'].sudo().search(
                [('e_commerce', '=', 'tiktok'), ('is_mapping_warehouse', '=', True)])
            if not warehouse:
                self.env['ir.logging'].sudo().create({
                    'name': 'create-refund-only-order-tiktok',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': "chưa có kho tiktok",
                    'func': 'create_refund_only_sale_order_tiktok',
                    'line': '0',
                })
            if len(reverse_list.get('return_item_list')) > 0:
                order.sudo().create_return_sale_order()
                so_return_and_refund = order.return_order_ids
                if so_return_and_refund:
                    order.sale_order_status = "giao_hang_that_bai"
                    so_return_and_refund.sudo().write({
                        'is_return_order_tiktok': True,
                        'refund_total_tiktok': float(reverse_list.get('refund_total')),
                        'source_id': self.env.ref('advanced_integrate_tiktok.utm_source_tiktok').id,
                        'warehouse_id': warehouse.id
                    })
                    product_id_return = []
                    for line_return in reverse_list.get('return_item_list'):
                        sku_product = line_return.get('seller_sku')
                        line = so_return_and_refund.order_line.filtered(lambda
                                                                            r: r.product_id.default_code == sku_product) if "," not in sku_product else so_return_and_refund.order_line.filtered(
                            lambda r: (r.product_id.marketplace_sku.encode('ascii', 'ignore')).decode(
                                "utf-8") == (sku_product.encode('ascii', 'ignore')).decode(
                                "utf-8") if r.product_id.marketplace_sku else r.product_id.marketplace_sku == sku_product)
                        if line:
                            line.product_uom_qty = -float(line_return.get('return_quantity'))
                            product_id_return.append(line.id)
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': 'create-refund-only-order-tiktok',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'path': 'url',
                                'message': "không có sản phẩm nào khớp với tiktok",
                                'func': 'create_refund_only_sale_order_tiktok',
                                'line': '0',
                            })

                    so_return_and_refund.order_line = [(6, 0, product_id_return)]
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'create-refund-only-order-tiktok',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': "chưa tạo được đơn return",
                        'func': 'create_refund_only_sale_order_tiktok',
                        'line': '0',
                    })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'create-refund-only-order-tiktok',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'create_refund_only_sale_order_tiktok',
                'line': '0',
            })

    ### end create refund only sale order tiktok

    ### start create return and refund sale order tiktok
    def create_return_and_refund_sale_order_tiktok(self, reverse_list, sale_order, status):
        try:
            # order = self.env['sale.order'].sudo().search([('tiktok_order_id', '=', order_id)], limit=1)
            search_order_return = sale_order.return_order_ids
            if status in (3, 4) and not search_order_return:
                if len(reverse_list.get('return_item_list')) > 0:
                    data = self._grooming_data_so_return_tiktok(reverse_list, sale_order, status)
                    if data is not None:
                        so_return_and_refund = self.env['sale.order'].sudo().create(data)
                        so_return_and_refund.name = so_return_and_refund.name + ' - Đổi trả đơn ' + sale_order.name
                        so_return_and_refund.sudo().action_confirm()
                    else:
                        self.env['ir.logging'].sudo().create({
                            'name': 'create-return-and-refund-order-tiktok',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'path': 'url',
                            'message': "chưa tạo được đơn return toàn phần",
                            'func': 'create_return_and_refund_sale_order_tiktok',
                            'line': '0',
                        })
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'create-return-and-refund-order-tiktok',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': "Return item list không có giá trị",
                        'func': 'create_return_and_refund_sale_order_tiktok',
                        'line': '0',
                    })
            elif status in [99, 100] and search_order_return:
                search_order_return.sudo().write({
                    's_tiktok_status_return': str(status),
                })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'create-return-and-refund-order-tiktok',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'create_return_and_refund_sale_order_tiktok',
                'line': '0',
            })
    ### end create return and refund sale order tiktok

    def _grooming_data_so_return_tiktok(self, reverse_list, order_id, status):
        so_line = []
        discount_refund = 0
        refund_total_tiktok = 0
        delivery_price = 0
        need_delivery = True
        warehouse = self.env['stock.warehouse'].sudo().search(
            [('e_commerce', '=', 'tiktok'), ('is_mapping_warehouse', '=', True)])
        if not warehouse:
            return None
        ###Kiểm tra xem đơn hàng có cần phí ship không
        order_line_id = len(order_id.order_line.filtered(lambda r: not r.is_delivery and not r.is_ecommerce_reward_line))
        return_item_list = len(reverse_list.get('return_item_list'))
        if return_item_list < order_line_id:
            need_delivery = False
        for item in reverse_list.get('return_item_list'):
            if len(order_id.order_line) > 0:
                ####Tìm line sản phẩm refund
                return_quantity = float(item.get('return_quantity'))
                seller_sku = item.get('seller_sku')
                if ',' not in seller_sku:
                    line = order_id.order_line.filtered(lambda r: r.product_id.default_code == seller_sku)
                else:
                    line = order_id.order_line.filtered(
                            lambda r: r.product_id.marketplace_sku != False and (
                                r.product_id.marketplace_sku.encode('ascii', 'ignore')).decode("utf-8") == (
                                          seller_sku.encode('ascii', 'ignore')).decode("utf-8"))
                if line:
                    if len(line) == 1:
                        order_lines = {
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'product_uom_qty': -return_quantity,
                            'product_uom': line.product_uom.id,
                            'price_unit': line.price_unit,
                            'refunded_orderline_id': line.id,
                            'tax_id': [(6, 0, line.tax_id.ids)] if line.tax_id else False,
                            'gift_card_id': False,
                            'coupon_program_id': False,
                            'is_line_coupon_program': False,
                            'is_ecommerce_reward_line': False,
                            'is_delivery': False,
                            'is_loyalty_reward_line': line.is_loyalty_reward_line,
                            's_loyalty_point_lines': line.s_loyalty_point_lines,
                            's_redeem_amount': line.s_redeem_amount,
                        }
                        so_line.append((0, 0, order_lines))
                        # if line.boo_total_discount_percentage > 0:
                        #     total_discount = (line.boo_total_discount_percentage / line.product_uom_qty) * return_quantity
                        #     discount_refund += total_discount
                    elif len(line) > 1:
                        for l in line:
                            order_lines = {
                                'gift_card_id': False,
                                'coupon_program_id': False,
                                'is_line_coupon_program': False,
                                'is_ecommerce_reward_line': False,
                                'is_delivery': False,
                            }
                            if l.product_uom_qty >= return_quantity:
                                order_lines.update({
                                    'product_id': l.product_id.id,
                                    'name': l.name,
                                    'product_uom_qty': -return_quantity,
                                    'product_uom': l.product_uom.id,
                                    'price_unit': l.price_unit,
                                    'is_loyalty_reward_line': l.is_loyalty_reward_line,
                                    's_loyalty_point_lines': l.s_loyalty_point_lines,
                                    's_redeem_amount': l.s_redeem_amount,
                                    'refunded_orderline_id': l.id,
                                    'tax_id': [(6, 0, l.tax_id.ids)] if l.tax_id else False,
                                })
                                so_line.append((0, 0, order_lines))
                                # if l.boo_total_discount_percentage > 0:
                                #     total_discount = (l.boo_total_discount_percentage / l.product_uom_qty) * return_quantity
                                #     discount_refund += total_discount
                                break
                            else:
                                order_lines.update({
                                    'product_id': l.product_id.id,
                                    'name': l.name,
                                    'product_uom_qty': -l.product_uom_qty,
                                    'product_uom': l.product_uom.id,
                                    'price_unit': l.price_unit,
                                    'is_loyalty_reward_line': l.is_loyalty_reward_line,
                                    's_loyalty_point_lines': l.s_loyalty_point_lines,
                                    's_redeem_amount': l.s_redeem_amount,
                                    'refunded_orderline_id': l.id,
                                    'tax_id': [(6, 0, l.tax_id.ids)] if l.tax_id else False,
                                })
                                so_line.append((0, 0, order_lines))
                                # if l.boo_total_discount_percentage > 0:
                                #     total_discount = l.boo_total_discount_percentage
                                #     discount_refund += total_discount
                                return_quantity = return_quantity - l.product_uom_qty

        ###Thêm line discount nếu có (tạm bỏ không dùng tới)
        # if discount_refund > 0:
        #     is_discount_line = self._get_line_discount_tiktok(discount_refund)
        #     if is_discount_line:
        #         is_discount_line.update({
        #             'product_uom_qty': -1
        #         })
        #         so_line.append((0, 0, is_discount_line))
        ##Đơn hàng bỏ không lấy phí ship
        # if need_delivery:
        #     is_delivery_line = order_id.order_line.filtered(lambda r: r.is_delivery)
        #     if is_delivery_line and is_delivery_line.product_uom_qty:
        #         is_delivery_line.product_id.lst_price = is_delivery_line.price_unit
        #         delivery_price = is_delivery_line.price_unit
        #         delivery_line = {
        #             'product_id': is_delivery_line.product_id.id,
        #             'name': is_delivery_line.name,
        #             'product_uom_qty': -1,
        #             'product_uom': is_delivery_line.product_uom.id,
        #             'price_unit': is_delivery_line.price_unit,
        #             'refunded_orderline_id': is_delivery_line.id,
        #             'tax_id': [(6, 0, is_delivery_line.tax_id.ids)] if is_delivery_line.tax_id else False,
        #             'is_line_coupon_program': is_delivery_line.is_line_coupon_program,
        #             'is_delivery': is_delivery_line.is_delivery,
        #         }
        #         so_line.append((0, 0, delivery_line))
        sale_order = {
            'partner_id': order_id.partner_id.id,
            'return_order_id': order_id.id,
            'payment_method': order_id.payment_method if order_id.payment_method else False,
            'order_line': so_line,
            'is_return_order': True,
            'is_return_order_tiktok': True,
            's_tiktok_status_return': '4' if status == 3 else str(status),
            'source_id': self.env.ref('advanced_integrate_tiktok.utm_source_tiktok').id,
            'warehouse_id': warehouse.id,
            'tiktok_order_id': order_id.tiktok_order_id,
            'tiktok_reverse_order_id': reverse_list.get('reverse_order_id')
        }
        return sale_order

    def _compute_total_line_so_return_tiktok(self):
        for rec in self:
            fee_delivery = 0
            need_delivery = True
            return_order_line_id = rec.return_order_id.order_line.filtered(lambda
                                       r: not r.is_delivery and not r.is_ecommerce_reward_line and r.product_id.detailed_type == 'product')
            order_line_id = rec.order_line.filtered(lambda
                                        r: not r.is_delivery and not r.is_ecommerce_reward_line and r.product_id.detailed_type == 'product')
            if len(order_line_id) < len(return_order_line_id):
                need_delivery = False
            is_delivery_line = rec.order_line.filtered(lambda r: r.is_delivery)
            if is_delivery_line:
                is_delivery_line.s_lst_price = is_delivery_line.price_unit
                is_delivery_line.product_id.lst_price = is_delivery_line.price_unit
                ###Return đủ sản phẩm -> có line ship
                if need_delivery:
                    if is_delivery_line.product_uom_qty >= 0:
                        is_delivery_line.product_uom_qty = -1
                    fee_delivery = is_delivery_line.price_unit * is_delivery_line.product_uom_qty
                else:
                    is_delivery_line.product_uom_qty = 0
            tax_totals_json = -rec.refund_total_tiktok
            is_discount_line = rec.order_line.filtered(lambda r: r.is_ecommerce_reward_line)
            if is_discount_line:
                total_discount = tax_totals_json - (sum(order_line_id.mapped('price_total')) + fee_delivery)
                if total_discount > 0:
                    is_discount_line.sudo().write({
                        'price_unit': - total_discount
                    })


class OrderCursor(models.Model):
    _name = 'cursor.tiktok'
    next_cursor = fields.Char("Cursor")
    more = fields.Boolean('More')
    cursor_type = fields.Char("Type")


class SSaleOrderError(models.Model):
    _name = "s.sale.order.error"
    _inherit = 'mail.activity.mixin'
    _order = 'create_date desc'
    tiktok_order_id = fields.Char()
    dbname = fields.Char()
    level = fields.Char()
    update_time = fields.Integer()
    message = fields.Char()
    return_created = fields.Boolean(default=False, string="Đã tạo lại đơn")
    active = fields.Boolean('Active', default=True)
    order_status = fields.Char()

    # @validate_integrate_token
    def _get_reverse_order_list_error(self, reverse_order_id):
        url_api = "/api/reverse/reverse_order/list"
        payload = {
            "offset": 0,
            "size": 20,
            "order_id": reverse_order_id
        }
        req = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload)).json()
        if req.get('code') == 0:
            return req.get('data')

    def user_canceled_order_tiktok_error(self, sale_order, pay_load):
        awaiting_shipment_status = '111'
        awaiting_collection_status = '112'
        is_tiktok_customer_canceled = False
        if sale_order.marketplace_tiktok_order_status in [awaiting_shipment_status, awaiting_collection_status]:
            if pay_load.get('cancel_user'):
                if pay_load.get('cancel_user') == 'SELLER':
                    is_tiktok_customer_canceled = False
                if pay_load.get('cancel_user') == 'BUYER':
                    is_tiktok_customer_canceled = True
                sale_order.sudo().write({
                    'is_tiktok_customer_canceled': is_tiktok_customer_canceled
                })

    def _grooming_return_order_tiktok_error(self, sale_order, picking_sale):
        picking_return = sale_order.picking_ids.filtered(lambda r: picking_sale.name in r.origin)
        if not picking_return:
            return_form = Form(
                self.env['stock.return.picking'].with_context(active_id=picking_sale.id, active_model='stock.picking'))
            wizard = return_form.save()
            return_do_picking = wizard.create_returns()
            if picking_sale.package_status == '5':
                sale_order.sudo().write({'sale_order_status': 'giao_hang_that_bai'})
            if return_do_picking:
                picking_return = sale_order.picking_ids.filtered(
                    lambda r: r.id == return_do_picking.get('res_id'))
                picking_return.action_set_quantities_to_reservation()
                # picking_return.button_validate()
                order_tiktok_do_return = sale_order.env['stock.picking'].sudo().search(
                    [('id', '=', return_do_picking.get('res_id'))])
                if order_tiktok_do_return and not order_tiktok_do_return.is_tiktok_do_return:
                    order_tiktok_do_return.write({'is_tiktok_do_return': True})
            return return_do_picking

    def _grooming_status_order_tiktok_error(self, pay_load, sale_order):
        data = pay_load.get('data')
        vals = {}
        if not sale_order.order_line.filtered(lambda l: l.is_delivery == True) or not \
                sale_order.picking_ids[0].package_tiktok_id:
            self.env['stock.picking']._mapping_package_shipping(sale_order, pay_load)
        if data.get('order_status'):
            convert_order_status = self.env['s.mkp.order.queue'].sudo().check_mkp_tiktok_order_status(sale_order, data)
            completed_date = None
            if data['order_status'] == "DELIVERED":
                if sale_order.marketplace_tiktok_order_status not in ['100', '111', '114', '130', '140']:
                    completed_date = datetime.fromtimestamp(data['update_time'])
            if data['order_status'] == "COMPLETED":
                if sale_order.sudo().sale_order_status not in ['hoan_thanh_1_phan', 'giao_hang_that_bai']:
                    completed_date = datetime.fromtimestamp(data['update_time'])
            if data['order_status'] == "CANCEL":
                if sale_order.marketplace_tiktok_order_status not in ['122', '130']:
                    completed_date = datetime.fromtimestamp(data['update_time'])
                    if pay_load.get('cancel_user'):
                        is_tiktok_customer_canceled = False
                    else:
                        is_tiktok_customer_canceled = True
                    vals['is_tiktok_customer_canceled'] = is_tiktok_customer_canceled
            if completed_date:
                if not sale_order.completed_date:
                    vals['completed_date'] = completed_date
            if convert_order_status != 0:
                vals['marketplace_tiktok_order_status'] = str(convert_order_status)
            if convert_order_status in ['121', '112', '122', '130']:
                if len(sale_order.picking_ids) > 0:
                    picking_ids = sale_order.picking_ids.filtered(lambda p: p.state not in (
                        'done', 'cancel'))
                    if len(picking_ids) > 0:
                        for picking in picking_ids:
                            if picking.state == 'confirmed':
                                picking.action_assign()
                                picking.sudo().action_set_quantities_to_reservation()
                            if picking.state == 'assigned':
                                picking.sudo().button_validate()
            elif convert_order_status == '140':
                picking_sale = sale_order.picking_ids.filtered(
                    lambda r: r.transfer_type == 'out' and r.location_id.usage in ('internal',))
                if picking_sale:
                    for picking in picking_sale:
                        if picking.state in ('assigned', 'confirmed'):
                            sale_order.picking_ids.action_cancel()
                            sale_order.action_cancel()
                        elif picking.state == 'done':
                            return_do_picking = self.env['s.mkp.order.queue']._grooming_return_order(sale_order, picking)
            if vals:
                sale_order.sudo().write(vals)
        else:
            self.env['s.sale.order.error'].sudo().create({
                'dbname': 'boo',
                'level': 'STATUS ERROR',
                'message': "Không có order_status trong data: %s" % str(pay_load),
                'tiktok_order_id': pay_load['data']['order_id'],
                'order_status': pay_load['data']['order_status'],
                'update_time': pay_load.get('data')['update_time']
            })

    def reverse_order_tiktok_error(self, pay_load, sale_order, reverse):
        if pay_load.get('data')['reverse_type'] == 1 and pay_load.get('data')['reverse_order_status'] != 1:
            if pay_load.get('data')['reverse_order_status'] == 51:
                picking_sale = sale_order.picking_ids.filtered(
                    lambda r: r.transfer_type == 'out' and r.location_id.usage in ('internal',))
                if picking_sale:
                    if sale_order.marketplace_tiktok_order_status in (
                            '111', '100') and picking_sale.state == 'assigned':
                        sale_order.picking_ids.action_cancel()
                        sale_order.action_cancel()
                    elif sale_order.marketplace_tiktok_order_status in (
                            '111', '112', '121') and picking_sale.state == 'done':
                        return_do_picking = self._grooming_return_order_tiktok_error(sale_order, picking_sale)
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': '#Tiktok: get_webhook_url',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': "Không có DO ",
                        'func': 'get_webhook_url',
                        'line': '0',
                    })
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Tiktok: get_webhook_url',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': "reverse_order_status != 51. Payload:%s" % str(
                        pay_load.get('data')),
                    'func': 'get_webhook_url',
                    'line': '0',
                })
        elif pay_load.get('data')['reverse_type'] == 2 and pay_load.get('data')['reverse_order_status'] != 1:
            if pay_load.get('data')['reverse_order_status'] in [4, 99, 100]:
                create_return_so = sale_order.sudo().create_return_and_refund_sale_order_tiktok(
                    reverse.get('reverse_list')[0], pay_load['data']['order_id'],
                    pay_load.get('data').get('reverse_order_status'))
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Tiktok: get_webhook_url',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': "reverse_order_status không ở trạng thái 4,99,100. Payload:%s" % str(
                        pay_load.get('data')),
                    'func': 'get_webhook_url',
                    'line': '0',
                })
            ### end create SO return tiktok
        elif pay_load.get('data')['reverse_type'] == 3 and pay_load.get('data')['reverse_order_status'] != 1:
            # if pay_load.get('data')['reverse_order_status'] == 4:
            #     create_return_so = sale_order.create_return_sale_order()
            ### start create SO return tiktok
            if pay_load.get('data').get('reverse_order_status') in (3, 4, 99, 100):
                create_reverse_order = self.env[
                    'sale.order'].sudo().create_return_and_refund_sale_order_tiktok(
                    reverse.get('reverse_list')[0], pay_load['data']['order_id'],
                    pay_load.get('data').get('reverse_order_status'))
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Tiktok: get_webhook_url',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': "reverse_order_status không ở trạng thái 4,99,100. Payload:%s" % str(
                        pay_load.get('data')),
                    'func': 'get_webhook_url',
                    'line': '0',
                })
            ### end start create SO return tiktok
        elif pay_load.get('data')['reverse_type'] == 4 and not len(sale_order.return_order_ids) and \
                pay_load.get('data')['reverse_order_status'] != 1:
            if pay_load.get('data')['reverse_order_status'] == 51:
                if sale_order.picking_ids.package_status in ("1", "2") and sale_order.picking_ids.state in (
                        'assigned'):
                    self.user_canceled_order_tiktok_error(sale_order=sale_order, pay_load=pay_load)
                    sale_order.picking_ids.action_cancel()
                    sale_order.sudo().write({
                        'sale_order_status': 'huy',
                        'marketplace_tiktok_order_status': '140'
                    })
                elif sale_order.picking_ids.package_status in (
                        "1", "2") and sale_order.picking_ids.state in ('done'):
                    self.user_canceled_order_tiktok_error(sale_order=sale_order, pay_load=pay_load)
                    sale_order.sudo().write({
                        'sale_order_status': 'huy',
                        'marketplace_tiktok_order_status': '140'
                    })
                    picking_sale = sale_order.picking_ids.filtered(lambda r: r.origin == sale_order.name)
                    return_do_picking = self._grooming_return_order_tiktok_error(sale_order, picking_sale)
                elif sale_order.picking_ids.package_status not in ("1", "2") and sale_order.picking_ids.state in (
                'done'):
                    picking_sale = sale_order.picking_ids.filtered(lambda r: r.origin == sale_order.name)
                    return_do_picking = self._grooming_return_order_tiktok_error(sale_order, picking_sale)
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': '#Tiktok: get_webhook_url',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': "state DO: %s \t Package_status: %s" % (
                            str(sale_order.picking_ids.state), str(sale_order.picking_ids.package_status)),
                        'func': 'get_webhook_url',
                        'line': '0',
                    })
        else:
            self.env['ir.logging'].sudo().create({
                'name': '#Tiktok: get_webhook_url',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': "pay_load.get('data')['reverse_type'] không ở trạng thái 1,2,3,4 or pay_load.get('data')['reverse_order_status'] =1. Payload:%s" % str(
                    pay_load.get('data')),
                'func': 'get_webhook_url',
                'line': '0',
            })

    def convert_status(self, orders_detail):
        status = False
        if orders_detail.get('order_list')[0].get('order_status') == 100:
            status = 'UNPAID'
        elif orders_detail.get('order_list')[0].get('order_status') == 111:
            status = 'AWAITING_SHIPMENT'
        elif orders_detail.get('order_list')[0].get('order_status') == 112:
            status = 'AWAITING_COLLECTION'
        elif orders_detail.get('order_list')[0].get('order_status') == 121:
            status = 'IN_TRANSIT'
        elif orders_detail.get('order_list')[0].get('order_status') == 122:
            status = 'DELIVERED'
        elif orders_detail.get('order_list')[0].get('order_status') == 130:
            status = 'COMPLETED'
        elif orders_detail.get('order_list')[0].get('order_status') == 140:
            status = 'CANCEL'
        return status

    # @validate_integrate_token
    def recreating_an_error_order(self):
        created_error = False
        context = {}
        search_order_fix = self.env['sale.order'].search([('tiktok_order_id', '=', self.tiktok_order_id)], limit=1)
        orders_detail = self.env['sale.order'].get_order_details(self.tiktok_order_id)
        if orders_detail is not None and not search_order_fix:
            customer_tiktok = self.env.ref('advanced_integrate_tiktok.s_res_partner_tiktok')
            if orders_detail.get('order_list'):
                for rec in orders_detail['order_list']:
                    query_warehouse = self._cr.execute(
                        """SELECT id FROM stock_warehouse WHERE s_warehouse_tiktok_id IS NOT NULL AND s_warehouse_tiktok_id = %s AND is_mapping_warehouse=TRUE limit 1""",
                        (rec['warehouse_id'],))
                    result_query_warehouse = [item[0] for item in self._cr.fetchall()]
                    if len(result_query_warehouse) > 0:
                        try:
                            note = "Thông tin khách hàng:\naddress_detail: %s\naddress_line_list: %s\ncity: %s\ndistrict: %s\nfull_address : %s\nname : %s\nphone: %s\nregion : %s\nstate: %s\ntown : %s" % (
                                rec['recipient_address']['address_detail'],
                                rec['recipient_address']['address_line_list'],
                                rec['recipient_address']['city'], rec['recipient_address']['district'],
                                rec['recipient_address']['full_address'], rec['recipient_address']['name'],
                                rec['recipient_address']['phone'], rec['recipient_address']['region'],
                                rec['recipient_address']['state'], rec['recipient_address']['town'])

                            product_orders = []
                            order = dict()
                            list_seller_sku = []
                            for line in rec.get('order_line_list'):
                                list_product = []
                                product_uom_qty = len([i for i in rec.get('order_line_list') if i.get('seller_sku') == line.get('seller_sku')])
                                if "," in line.get('seller_sku'):
                                    seller_sku = line.get('seller_sku').split(',')
                                    for r in seller_sku:
                                        if r not in list_seller_sku:
                                            product_product = self.env['product.product'].sudo().search(
                                                [('marketplace_sku', '=', line.get('seller_sku')),
                                                 ('default_code', '=', (r.encode('ascii', 'ignore')).decode("utf-8")),
                                                 ('to_sync_tiktok', '=', True)])
                                            if product_product:
                                                stock_quant = product_product.stock_quant_ids.filtered(
                                                    lambda r: r.location_id.warehouse_id.id == result_query_warehouse[
                                                        0] and r.available_quantity > 0 and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id)
                                                stock_available = stock_quant.available_quantity
                                                if stock_available and stock_available > 0:
                                                    if stock_available >= product_uom_qty and len(list_product) == 0:
                                                        product = {
                                                            'product_id': product_product.id,
                                                            'name': product_product.name,
                                                            'stock_available': product_uom_qty,
                                                            'uom_id': product_product.uom_id.id
                                                        }
                                                        list_seller_sku.append(r)
                                                        list_product.append(product)
                                                        product_uom_qty = 0
                                                        break
                                                    elif (stock_available < product_uom_qty) or len(list_product):
                                                        if product_uom_qty > 0:
                                                            if stock_available < product_uom_qty:
                                                                product = {
                                                                    'product_id': product_product.id,
                                                                    'name': product_product.name,
                                                                    'stock_available': stock_available,
                                                                    'uom_id': product_product.uom_id.id
                                                                }
                                                                list_seller_sku.append(r)
                                                                product_uom_qty -= stock_available
                                                                list_product.append(product)
                                                            else:
                                                                product = {
                                                                    'product_id': product_product.id,
                                                                    'name': product_product.name,
                                                                    'stock_available': product_uom_qty,
                                                                    'uom_id': product_product.uom_id.id
                                                                }
                                                                list_seller_sku.append(r)
                                                                product_uom_qty = 0
                                                                list_product.append(product)
                                                        else:
                                                            break
                                        else:
                                            product_uom_qty = 0
                                    if product_uom_qty > 0:
                                        created_error = True
                                        context['message'] = "product: %s không đủ tồn" % line.get(
                                            'product_name')
                                else:
                                    product_product = self.env['product.product'].sudo().search(
                                        [('default_code', '=', line.get('seller_sku')), ('to_sync_tiktok', '=', True)])
                                    if product_product:
                                        stock_available = product_product.stock_quant_ids.filtered(
                                            lambda r: r.location_id.warehouse_id.id == result_query_warehouse[
                                                0] and r.available_quantity > 0 and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).available_quantity
                                        if stock_available and stock_available >= product_uom_qty:
                                            product = {
                                                'product_id': product_product.id,
                                                'name': product_product.name,
                                                'stock_available': product_uom_qty,
                                                'uom_id': product_product.uom_id.id
                                            }
                                            if line.get('seller_sku') not in list_seller_sku:
                                                list_seller_sku.append(line.get('seller_sku'))
                                                list_product.append(product)
                                        else:
                                            created_error = True
                                            context[
                                                'message'] = "product: %s không đủ tồn" % product_product.name
                                    else:
                                        created_error = True
                                        context['message'] = "Không có sản phẩm nào khớp với Tiktok trên odoo"
                                if list_product:
                                    ###Kiểm tra price_unit xem sản phẩm có được chiết khấu không
                                    if not line.get('seller_discount'):
                                        s_price_unit = line.get('original_price')
                                    else:
                                        s_price_unit = line.get('original_price') - line.get('seller_discount')
                                    for record in list_product:
                                        product_orders.append(
                                            {
                                                "product_id": record.get('product_id'),
                                                "name": record.get('name'),
                                                "product_uom": record.get('uom_id'),
                                                "product_uom_qty": record.get('stock_available'),
                                                "price_unit": s_price_unit,
                                                "s_lst_price": line.get('original_price'),
                                            })
                            if len(product_orders) > 0 and len(product_orders) >= len(
                                    rec['item_list']) and not created_error:
                                source_id = self.env.ref('advanced_integrate_tiktok.utm_source_tiktok')
                                order['partner_id'] = customer_tiktok.id
                                order['partner_invoice_id'] = customer_tiktok.id
                                order['partner_shipping_id'] = customer_tiktok.id
                                order['tiktok_order_id'] = rec['order_id']
                                order['note'] = note
                                order['is_tiktok_order'] = True
                                order['marketplace_tiktok_order_status'] = str(rec['order_status'])
                                order['warehouse_id'] = result_query_warehouse[0]
                                order['currency_id'] = self.env.company.currency_id.id
                                order['source_id'] = source_id.id
                                order['payment_method'] = "cod" if rec['is_cod'] else "online"
                                ####update ngày đặt hàng (create_time)
                                if rec.get('create_time'):
                                    if len(str(rec.get('create_time'))) == 13:
                                        order['date_order'] = datetime.fromtimestamp(int(rec.get('create_time')) / 1000)
                                    else:
                                        order['date_order'] = datetime.fromtimestamp(int(rec.get('create_time')))
                                order_lines = []
                                if str(rec['order_status']) in ('122', '130', '140') and rec.get('update_time'):
                                    order['completed_date'] = datetime.fromtimestamp(int(rec.get('update_time')))
                                for product_order in product_orders:
                                    order_lines.append((0, 0, {
                                        'product_id': product_order['product_id'],
                                        'name': product_order['name'],
                                        'product_uom_qty': product_order['product_uom_qty'],
                                        'product_uom': product_order['product_uom'],
                                        'price_unit': product_order['price_unit'],
                                        's_lst_price': product_order['s_lst_price'],
                                        'is_product_reward': False
                                    }))
                                    ###Bỏ line chiết khấu sàn marketplace
                                    ###Check chiết khấu của sàn tiktok
                                    # if rec.get('payment_info').get('platform_discount') is not None:
                                    #     discount_price = int(rec.get('payment_info').get('platform_discount'))
                                    #     if discount_price > 0:
                                    #         is_discount_line = self.env['sale.order'].sudo()._get_line_discount_tiktok(
                                    #             discount_price)
                                    #         if is_discount_line:
                                    #             order_lines.append((0, 0, is_discount_line))
                                if len(order_lines) > 0:
                                    order['order_line'] = order_lines
                                if order is not None:
                                    created_order = self.env['sale.order'].sudo().create(order)
                                    self.sudo().write({
                                        'return_created': True
                                    })
                                    ###Bỏ line phí ship đơn marketplace
                                    # if 'shipping_provider' in orders_detail.get('order_list')[0]:
                                    #     shipping_provider = orders_detail.get('order_list')[0].get('shipping_provider')
                                    #     if orders_detail.get('order_list')[0].get('payment_info'):
                                    #         payment_info = orders_detail.get('order_list')[0].get('payment_info')
                                    #         if payment_info.get('shipping_fee'):
                                    #             shipping_price = payment_info.get('shipping_fee')
                                    #             get_shipping_method = self.env['s.sale.order.error'].sudo()._get_shipping_method_tiktok(
                                    #                 shipping_provider, shipping_price)
                                    #             if get_shipping_method:
                                    #                 created_order.carrier_id = get_shipping_method['carrier_id']
                                    #                 is_delivery_line = created_order._create_delivery_line(get_shipping_method['carrier_id'], shipping_price)
                                    #                 if is_delivery_line:
                                    #                     is_delivery_line.sudo().write({
                                    #                         'price_unit': shipping_price
                                    #                     })
                                    created_order.sudo().action_confirm()

                                    ###mapping package_status and package_tiktok_id
                                    if orders_detail.get('order_list')[0].get('package_list'):
                                        self.env['stock.picking'].sudo().s_get_package_id_tiktok(orders_detail, created_order)
                                    ###Sau khi order confirm mới cho write date_order
                                    if order.get('date_order'):
                                        created_order.sudo().write({
                                            'date_order': order.get('date_order')
                                        })
                                    if created_order.marketplace_tiktok_order_status in ('121', '112', '122', '130'):
                                        if len(created_order.picking_ids) > 0:
                                            picking_ids = created_order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                                            if len(picking_ids) > 0:
                                                for picking in picking_ids:
                                                    if picking.state == 'confirmed':
                                                        picking.action_assign()
                                                        picking.sudo().action_set_quantities_to_reservation()
                                                    if picking.state == 'assigned':
                                                        picking.sudo().button_validate()
                                    elif created_order.marketplace_tiktok_order_status == '140':
                                        picking_sale = created_order.picking_ids.filtered(
                                            lambda r: r.transfer_type == 'out' and r.location_id.usage in ('internal',))
                                        if picking_sale:
                                            for picking in picking_sale:
                                                if picking.state in ('assigned', 'confirmed'):
                                                    created_order.picking_ids.action_cancel()
                                            created_order.action_cancel()
                                    if order.get('completed_date') and not created_order.completed_date:
                                        created_order.sudo().write({
                                            'completed_date': order.get('completed_date')
                                        })
                        except Exception as e:
                            created_error = True
                            context['message'] = str(e)
        elif orders_detail is not None and search_order_fix:
            if search_order_fix.sale_order_status not in ('hoan_thanh', 'huy'):
                status = self.sudo().convert_status(orders_detail)
                if status:
                    pay_load = {
                        "cancel_user": orders_detail.get('order_list')[0].get('cancel_user') if
                        orders_detail.get('order_list')[0].get('cancel_user') else False,
                        "data": {
                            "order_id": str(search_order_fix.tiktok_order_id),
                            "order_status": str(status),
                            "update_time": orders_detail.get('order_list')[0].get('update_time')
                        }
                    }
                    self._grooming_status_order_tiktok_error(pay_load, search_order_fix)
                    if status == 'COMPLETED':
                        reverse = self._get_reverse_order_list_error(search_order_fix.tiktok_order_id)
                        if reverse.get('reverse_list'):
                            pay_load_reverse = {
                                "data": {
                                    "order_id": str(search_order_fix.tiktok_order_id),
                                    "reverse_type": reverse.get('reverse_list')[0].get('reverse_type'),
                                    "reverse_order_status": reverse.get('reverse_list')[0].get('reverse_status_value'),
                                    "reverse_order_id": str(reverse.get('reverse_list')[0].get('reverse_order_id')),
                                    "update_time": str(reverse.get('reverse_list')[0].get('reverse_update_time'))
                                }
                            }
                            self.reverse_order_tiktok_error(pay_load_reverse, search_order_fix, reverse)
            elif search_order_fix.sale_order_status in ('hoan_thanh',):
                reverse = self._get_reverse_order_list_error(search_order_fix.tiktok_order_id)
                if reverse.get('reverse_list'):
                    pay_load_reverse = {
                        "data": {
                            "order_id": str(search_order_fix.tiktok_order_id),
                            "reverse_type": reverse.get('reverse_list')[0].get('reverse_type'),
                            "reverse_order_status": reverse.get('reverse_list')[0].get('reverse_status_value'),
                            "reverse_order_id": str(reverse.get('reverse_list')[0].get('reverse_order_id')),
                            "update_time": str(reverse.get('reverse_list')[0].get('reverse_update_time'))
                        }
                    }
                    self.reverse_order_tiktok_error(pay_load_reverse, search_order_fix, reverse)
            self.sudo().write({
                'return_created': True
            })

        else:
            created_error = True
            context['message'] = "Kiểm tra lại order và token"
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
            rec_unlink = self.sudo().search([('tiktok_order_id', '=', self.tiktok_order_id)])
            if rec_unlink:
                rec_unlink.unlink()
            return {
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': '{base_url}/web#view_type=list&model=s.sale.order.error&action={action_sale}'.format(
                    base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                    action_sale=self.env.ref('advanced_integrate_tiktok.s_sale_order_error_act_window').id)
            }
        # elif not created_error and self.return_created:
        #     self.ids = [(2, self.id)]
        #     a = 0

    # def _get_shipping_method_tiktok(self, shipping_provider=False, shipping_price=False):
    #     order_line = False
    #     if shipping_provider and shipping_price:
    #         shipping_method = self.env['delivery.carrier'].sudo().search([('name', 'ilike', shipping_provider)],
    #                                                                      limit=1)
    #         if shipping_method:
    #             shipping_method_product_old_value = self.env['product.product'].sudo().search([
    #                 ('id', '=', shipping_method.product_id.id)
    #             ])
    #             shipping_method_product_old_value.write({
    #                 'lst_price': float(shipping_price) if shipping_price else 0,
    #                 'la_phi_ship_hang_m2': True
    #             })
    #             if not shipping_method.product_id:
    #                 raise ValidationError('Product service does not exits!')
    #             if float(shipping_price) > 0:
    #                 order_line = {
    #                     "product_id": shipping_method.product_id.id,
    #                     "carrier_id": shipping_method,
    #                     "product_uom_qty": 1,
    #                     "price_unit": shipping_method_product_old_value.lst_price,
    #                     "s_lst_price": shipping_method_product_old_value.lst_price,
    #                     "is_delivery": True,
    #                 }
    #         else:
    #             shipping_method_product_new_value = self.env['product.product'].sudo().create({
    #                 'name': shipping_provider,
    #                 'detailed_type': 'service',
    #                 'lst_price': float(shipping_price) if shipping_price else 0,
    #                 'la_phi_ship_hang_m2': True
    #             })
    #             if shipping_method_product_new_value:
    #                 shipping_method_new = self.env['delivery.carrier'].sudo().create({
    #                     'name': shipping_provider,
    #                     'delivery_type': 'fixed',
    #                     # 'invoice_policy': 'real',
    #                     'product_id': shipping_method_product_new_value.id
    #                 })
    #                 if shipping_method_product_new_value.lst_price > 0:
    #                     order_line = {
    #                         "product_id": shipping_method_new.product_id.id,
    #                         "carrier_id": shipping_method_new,
    #                         "product_uom_qty": 1,
    #                         "price_unit": shipping_method_product_new_value.lst_price,
    #                         "s_lst_price": shipping_method_product_new_value.lst_price,
    #                         "is_delivery": True,
    #                     }
    #     return order_line

    def _compute_delete_record_recreate_tiktok(self):
        for rec in self:
            tiktok_order_id = self.env['sale.order'].sudo().search(
                [('tiktok_order_id', '=', rec.tiktok_order_id), ('is_tiktok_order', '=', True)], limit=1)
            if tiktok_order_id:
                if rec.level == "ERROR":
                    rec.unlink()
                else:
                    if tiktok_order_id.sale_order_status in ['da_giao_hang', 'hoan_thanh', 'huy']:
                        rec.unlink()
