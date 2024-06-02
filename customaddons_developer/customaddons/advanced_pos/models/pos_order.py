from odoo import fields, models, api
from odoo.osv.expression import AND
import json
import time
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError, UserError
import pytz
import re


class SPosOrderInherit(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'mail.thread']
    sale_person_id = fields.Many2one('hr.employee', string='Nhân viên bán hàng')
    is_bag = fields.Boolean(
        string='Không lấy túi', default=False)
    is_bill = fields.Boolean(
        string='Không lấy bill', default=False)
    payment_method = fields.Char(string="Thanh toán", compute="_compute_payment_method", store=True)
    payment_note_order = fields.Char(string="Ghi chú thành toán", compute="_compute_payment_method", store=True)
    pos_name = fields.Char('Điểm bán hàng', related='config_id.name', store=True)
    # applied_promotion_program = fields.Char(string="Chương trình khuyến mãi",
    #                                         related='applied_program_ids.name', store=True)
    applied_promotion_program = fields.Char(string="Chương trình khuyến mãi",
                                            compute='_compute_apply_promotion_program', store=True)
    customer_phone = fields.Char(string="Số điện thoại", related='partner_id.phone', groups="advanced_sale.s_boo_group_administration,advanced_sale.s_boo_group_ecom,advanced_sale.s_boo_group_area_manager,advanced_sale.s_boo_group_hang_hoa,advanced_sale.s_boo_group_dieu_phoi,advanced_sale.s_boo_group_ke_toan")
    # customer_ranked = fields.Char(string="Hạng", related='partner_id.customer_ranked', store=True)
    customer_ranked = fields.Char(string="Hạng", compute='_compute_partner_customer_ranked', store=True)
    pos_order_status = fields.Selection([
        ('moi', 'Mới'),
        ('hoan_thanh', 'Hoàn thành'),
        ('da_huy', 'Đã hủy'),
    ], string='Tình trạng đơn hàng', tracking=True, compute="_compute_pos_order_state", store=True, default='moi')
    is_cancel_order = fields.Boolean(string="Là đơn hàng Hủy", default=False)
    is_refund_order = fields.Boolean(string="Là đơn hàng trả lại", compute="compute_s_refund_order", store=True)
    total_quantity_pos = fields.Integer(string='Tổng số lượng sản phẩm', compute='_compute_total_quantity_pos', store=True)
    tong_chiet_khau = fields.Float(string='Tổng chiết khấu', compute='_compute_tong_chiet_khau', store=True)
    s_store_code = fields.Char(string='Mã kho dành cho DWH', compute="_compute_pos_order_config_id_code",
                               store=True)
    date_order_pos_filter = fields.Datetime(string="Date filter", compute="_compute_date_order_pos_filter", store=True)
    is_order_duplicate = fields.Boolean(string="Là đơn hàng có thể bị duplicate", default=False)
    order_duplicate_origin = fields.Char(string="Đơn hàng có thể bị duplicate")
    is_compute_coupon_program = fields.Boolean(string='Đã compute lại coupon program', default=False)
    source_id = fields.Many2one('utm.source', 'Source')
    sale_order_id_dashboard = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    s_is_admin = fields.Boolean(string='Is Admin', compute='_compute_s_is_admin')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(SPosOrderInherit, self).fields_get(allfields, attributes)
        hide_list = ['partner_id']
        user = self.env.user
        user_group_has_access = [user.has_group('advanced_sale.s_boo_group_administration'),
                                 user.has_group('advanced_sale.s_boo_group_area_manager'),
                                 user.has_group('advanced_sale.s_boo_group_ecom')]
        user_group_thu_ngan = user.has_group('advanced_sale.s_boo_group_thu_ngan')
        if user_group_thu_ngan and not any(user_group_has_access):
            for field in hide_list:
                if res.get(field):
                    res[field]['exportable'] = False
        return res

    def _compute_s_is_admin(self):
        for r in self:
            r.s_is_admin = self.env.user.has_group('advanced_sale.s_boo_group_administration') or self.env.user.has_group('base.group_system')

    def _export_for_ui(self, order):
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        return {
            'lines': [[0, 0, line] for line in order.lines.export_for_ui()],
            'statement_ids': [[0, 0, payment] for payment in order.payment_ids.export_for_ui()],
            'name': order.pos_reference,
            'uid': order.pos_reference.replace(re.sub('([0-9]|-)','', order.pos_reference), ''),
            'amount_paid': order.amount_paid,
            'amount_total': order.amount_total,
            'amount_tax': order.amount_tax,
            'amount_return': order.amount_return,
            'pos_session_id': order.session_id.id,
            'is_session_closed': order.session_id.state == 'closed',
            'pricelist_id': order.pricelist_id.id,
            'partner_id': order.partner_id.id,
            'user_id': order.user_id.id,
            'sequence_number': order.sequence_number,
            'creation_date': order.date_order.astimezone(timezone),
            'fiscal_position_id': order.fiscal_position_id.id,
            'to_invoice': order.to_invoice,
            'to_ship': order.to_ship,
            'state': order.state,
            'account_move': order.account_move.id,
            'id': order.id,
            'is_tipped': order.is_tipped,
            'tip_amount': order.tip_amount,
        }

    def write(self, vals):
        if vals.get('note'):
            for r in self:
                self._cr.execute(
                    """UPDATE pos_order SET note = %s WHERE id = %s""",
                    (vals.get('note'), r.id))
            vals.pop('note')
        else:
            return super(SPosOrderInherit, self).write(vals)

    @api.depends('partner_id.customer_ranked')
    def _compute_partner_customer_ranked(self):
        for r in self:
            if r.ids:
                customer_ranked_old = r.customer_ranked
                self._cr.execute(
                    """UPDATE pos_order SET customer_ranked = %s WHERE id = %s""",
                    (False, r.ids[0]))
                if customer_ranked_old:
                    self._cr.execute(
                        """UPDATE pos_order SET customer_ranked = %s WHERE id = %s""",
                        (customer_ranked_old, r.ids[0]))
                if r.partner_id.customer_ranked and r.partner_id.customer_ranked != customer_ranked_old:
                    self._cr.execute(
                        """UPDATE pos_order SET customer_ranked = %s WHERE id = %s""",
                        (r.partner_id.customer_ranked, r.ids[0]))
            else:
                r.customer_ranked = False

    def _compute_source_id_report_order(self, type=False):
        if type == 1:
            pos_source_id = self.env.ref('advanced_sale.utm_source_pos_order')
            if pos_source_id:
                query_update_pos_order = self._cr.execute("""UPDATE pos_order SET source_id = %s WHERE source_id IS NULL""",
                                                      (pos_source_id.id,))
        elif type == 2:

            sale_source_id = self.env.ref('advanced_sale.utm_source_sale')
            ban_buon_source_id = self.env.ref('advanced_sale.utm_source_sell_wholesale')
            magento_source_id = self.env.ref('advanced_sale.utm_source_magento_order')
            ##Magento
            if magento_source_id:
                query_update_magento_order = self._cr.execute("""UPDATE sale_order SET source_id = %s WHERE is_magento_order IS TRUE AND source_id IS NULL""",
                                                      (magento_source_id.id, ))
            if sale_source_id:
                query_update_sale_order = self._cr.execute(
                    """UPDATE sale_order SET source_id = %s WHERE is_magento_order IS FALSE 
                        AND (is_sell_wholesale IS FALSE OR is_sell_wholesale IS NULL)
                        AND (is_tiktok_order IS FALSE OR is_tiktok_order IS NULL)
                        AND (is_lazada_order IS FALSE OR is_lazada_order IS NULL)""",
                    (sale_source_id.id,))
            if ban_buon_source_id:
                query_update_ban_buon_order = self._cr.execute(
                    """UPDATE sale_order SET source_id = %s WHERE is_sell_wholesale IS TRUE""",
                    (ban_buon_source_id.id,))
        elif type == 3:
            ###Facebook, Zalo
            query_fb_order = self._cr.execute("""UPDATE sale_order SET is_magento_order=TRUE WHERE id in
            (SELECT id FROM sale_order WHERE source_id IN (SELECT id FROM utm_source WHERE name ilike 'Facebook') AND is_magento_order IS FALSE)""")
            query_zalo_order = self._cr.execute("""UPDATE sale_order SET is_magento_order=TRUE WHERE id in
                        (SELECT id FROM sale_order WHERE source_id IN (SELECT id FROM utm_source WHERE name ilike 'Zalo') AND is_magento_order IS FALSE)""")

    def compute_pos_order_lost_coupon_program(self):
        search_order_line = self._cr.execute("""
            select order_id from pos_order_line where coupon_id is null 
            and program_id is null 
            and price_unit < 0 and gift_card_id is null 
            and is_line_gift_card is false and qty != 0 
            and refunded_orderline_id is null;
        """)
        result_search_order_line = [res[0] for res in self._cr.fetchall()]
        if len(result_search_order_line) > 0:
            for rec in result_search_order_line:
                order = self.browse(rec)
                order_line_promo = order.lines.filtered(lambda l: l.product_id.from_coupon_program)
                if order_line_promo:
                    order.write({
                        'applied_program_ids': order.lines.product_id.from_coupon_program
                    })
                    line_product = order.lines.filtered(lambda l: l.product_id.detailed_type == 'product')
                    for line in order_line_promo:
                        promo = line.product_id.from_coupon_program
                        if promo.program_type == 'promotion_program':
                            line.sudo().write({
                                'program_id': line.product_id.from_coupon_program.id
                            })
                        else:
                            line.sudo().write({
                                'coupon_id': line.product_id.from_coupon_program.id
                            })
                    if line_product:
                        self.env['pos.order.line']._link_line_lost_promo(line_product)

    @api.depends('lines')
    def _compute_apply_promotion_program(self):
        for rec in self:
            rec.applied_promotion_program = ''
            if rec.lines:
                for r in rec.lines:
                    if r.program_id:
                        rec.applied_promotion_program += r.program_id.name + ', '
            rec.applied_promotion_program = rec.applied_promotion_program.rstrip(', ')

    @api.depends('date_order')
    def _compute_date_order_pos_filter(self):
        for rec in self:
            if rec.date_order:
                rec.date_order_pos_filter = rec.date_order + timedelta(hours=7)

    @api.depends('config_id')
    def _compute_pos_order_config_id_code(self):
        for rec in self:
            rec.s_store_code = ''
            if rec.config_id:
                if rec.config_id.code:
                    rec.s_store_code = rec.config_id.code
            order_line_ids = rec.lines.filtered(lambda l: l.product_id.type == 'product')
            if order_line_ids:
                for line in order_line_ids:
                    line.s_store_code = rec.s_store_code

    @api.depends('lines')
    def _compute_tong_chiet_khau(self):
        for rec in self:
            temp_sum = 0
            if rec.lines:
                for line in rec.lines:
                    temp_sum += line.boo_total_discount_percentage + line.boo_total_discount
                rec.tong_chiet_khau = temp_sum

    def force_unlink_cancel_order(self):
        src_order = []
        if self.env.user.has_group('advanced_sale.s_boo_group_administration'):
            if self.is_cancel_order:
                if self.refunded_order_ids:
                    for ro in self.refunded_order_ids:
                        src_order.append(ro)
                # Xóa đơn hàng hiện tại
                self.sudo().unlink()
        if len(src_order) > 0:
            # Bỏ tích đơn hàng gốc là đơn hàng hủy đi
            for so in src_order:
                so.sudo().write({
                    'is_cancel_order': False,
                    'is_refund_order': False,
                })
            view_id = self.env.ref('point_of_sale.view_pos_pos_form').id
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pos.order',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'main',
                'res_id': src_order[0].id,
            }
        action = self.env.ref('point_of_sale.action_pos_pos_form').sudo().read()[0]
        action['target'] = 'main'
        return action

    @api.depends('lines')
    def _compute_total_quantity_pos(self):
        for rec in self:
            total_product_minus = 0
            total_product_positive = 0
            rec.total_quantity_pos = 0
            if rec.lines:
                # total_product = 0
                for line in rec.lines:
                    if line.product_id.detailed_type == 'product':
                        if line.qty < 0:
                            total_product_minus += line.qty
                        else:
                            total_product_positive += line.qty
                rec.total_quantity_pos = abs(total_product_minus) + total_product_positive

    @api.depends('lines.refund_orderline_ids', 'is_cancel_order')
    def compute_s_refund_order(self):
        for order in self:
            is_refund_order = False
            refund_orders_count = len(order.mapped('lines.refund_orderline_ids.order_id'))
            if refund_orders_count > 0 and not order.is_cancel_order:
                is_refund_order = True
            order.sudo().is_refund_order = is_refund_order

    def refund(self):
        # Đơn hàng đã có trả hàng rồi thì không hủy được nữa
        if self.refund_orders_count > 0:
            raise UserError('Không thể hủy đơn hàng đã được trả hàng.')
        res = super(SPosOrderInherit, self).refund()
        for rec in self:
            rec.sudo().is_cancel_order = True
        if 'res_id' in res:
            cancel_order = self.env['pos.order'].sudo().browse(res['res_id'])
            for r in cancel_order:
                r.sudo().is_cancel_order = True
                r.loyalty_points = -r.loyalty_points
                self.sudo().partner_id.loyalty_points = self.sudo().partner_id.loyalty_points + r.loyalty_points
                # history_points_id = self.env['s.order.history.points'].sudo().search([('order_id', '=', r.id)])
                # if history_points_id:
                #     history_points_id.sudo().write({
                #         'diem_cong': -(history_points_id.diem_cong)
                #     })
            if cancel_order and cancel_order.pos_reference:
                new_pos_reference = ""
                if 'Đơn hàng' in cancel_order.pos_reference:
                    new_pos_reference = cancel_order.pos_reference.replace('Đơn hàng', 'C -')
                else:
                    new_pos_reference = cancel_order.pos_reference.replace('Order', 'C -')
                cancel_order.sudo().pos_reference = new_pos_reference
        return res

    def update_duplicate_pos_reference(self):
        new_pos_reference = '-R'
        for rec in self:
            exist_pos_reference = rec.env['pos.order'].search([('pos_reference', '=', rec.pos_reference)])
            if len(exist_pos_reference) > 1 and rec.pos_reference and new_pos_reference not in rec.pos_reference and rec.amount_paid <= 0 and 'HOÀN TIỀN' in rec.name:
                rec.pos_reference += new_pos_reference

    @api.depends('payment_ids')
    def _compute_payment_method(self):
        for r in self:
            payment_method = ''
            payment_note_order = ''
            for pos_payment in r.payment_ids:
                if pos_payment.payment_note:
                    payment_note_order += pos_payment.payment_note + ', '
                if pos_payment.payment_method_id:
                    payment_method += pos_payment.payment_method_id.name + ', '
            r.sudo().payment_note_order = payment_note_order.rstrip(', ')
            r.sudo().payment_method = payment_method.rstrip(', ')

    @api.depends('state', 'is_cancel_order')
    def _compute_pos_order_state(self):
        for r in self:
            if r.pos_order_status not in ['hoan_thanh']:
                r.pos_order_status = 'moi'
                if r.state == 'draft':
                    r.sudo().write({
                        'pos_order_status': 'moi'
                    })
                elif r.state == 'cancel':
                    r.sudo().write({
                        'pos_order_status': 'da_huy'
                    })
                elif r.state == 'invoiced':
                    r.sudo().write({
                        'pos_order_status': 'hoan_thanh'
                    })

    @api.model
    def search_paid_order_ids(self, config_id, domain, limit, offset):
        """Search for 'paid' orders that satisfy the given domain, limit and offset."""
        if config_id == []:
            default_domain = ['&', ('config_id', '!=', False), '!', '|', ('state', '=', 'draft'),
                              ('state', '=', 'cancelled')]
        else:
            default_domain = ['&', ('config_id', '=', config_id), '!', '|', ('state', '=', 'draft'),
                              ('state', '=', 'cancelled')]
        real_domain = AND([domain, default_domain])
        ids = self.search(AND([domain, default_domain]), limit=limit, offset=offset).ids
        totalCount = self.search_count(real_domain)
        return {'ids': ids, 'totalCount': totalCount}

    @api.model
    def _order_fields(self, ui_order):
        # if len(ui_order['bookedCouponCodes']) > 0:
        #     for coupon in ui_order['bookedCouponCodes']:
        #         self._cr.execute("""UPDATE coupon_coupon SET state = 'used' WHERE boo_code = '%s'""" % (str(coupon),))
        order_fields = super(SPosOrderInherit, self)._order_fields(ui_order)
        order_fields['sale_person_id'] = ui_order.get('sale_person_id')
        order_fields['is_bag'] = ui_order.get('is_bag')
        order_fields['is_bill'] = ui_order.get('is_bill')
        order_fields['is_order_duplicate'] = ui_order.get('is_order_duplicate')
        order_fields['order_duplicate_origin'] = ui_order.get('order_duplicate_origin')
        pos_source_id = self.env.ref('advanced_sale.utm_source_pos_order')
        if pos_source_id:
            order_fields['source_id'] = pos_source_id.id
        return order_fields

    def _process_order(self, order, draft, existing_order):
        #Đổi state coupon sau khi tạo đơn hàng pos
        pos_order_id = super(SPosOrderInherit, self)._process_order(order, draft, existing_order)
        if pos_order_id:
            search_order = self.env['pos.order'].browse(pos_order_id)
            line_coupon_id = search_order.lines.filtered(lambda l: l.coupon_id and l.program_id)
            if line_coupon_id:
                if len(order['data'].get('bookedCouponCodes')) > 0:
                    coupon_program = order['data'].get('bookedCouponCodes')
                    ###trong orderline có line coupon -> mới cho thay đổi state
                    for code in coupon_program:
                        coupon = coupon_program[code]
                        if line_coupon_id.filtered(lambda r: r.coupon_id.boo_code == code and r.coupon_id.id == coupon_program[code].get('coupon_id')):
                            self._cr.execute("""UPDATE coupon_coupon SET state = 'used', pos_order_id = %s 
                            WHERE boo_code = '%s' and id = %s """ % (pos_order_id, str(coupon.get('code')),coupon.get('coupon_id')))
        return pos_order_id

    def create(self, vals_list):
        res = super(SPosOrderInherit, self).create(vals_list)
        if res.partner_id:
            res.partner_id._edit_last_order()
            # if res.state in ('paid', 'done', 'invoiced'):
            count_partner_order = len(res.partner_id.sale_order_ids) + len(res.partner_id.pos_order_ids)
            if count_partner_order == 1:
                res.sudo().partner_id.write({
                    'is_new_customer': True,
                })
                if res.partner_id.pos_create_customer is False:
                    res.sudo().partner_id.write({
                        'pos_create_customer': res.config_id.name,
                        's_pos_order_id': res.config_id,
                    })
            else:
                res.sudo().partner_id.write({
                    'is_new_customer': False,
                })
            try:
                # lich su tich diem
                if res.loyalty_points:
                    data_points = {
                        'diem_cong': res.loyalty_points if res.amount_total > 0 else - abs(res.loyalty_points),
                        'ly_do': 'Điểm trên đơn hàng POS',
                        'res_partner_id': res.partner_id.id
                    }
                    if res._name == 'sale.order':
                        data_points['sale_order_id'] = res.id
                    else:
                        data_points['order_id'] = res.id
                    self.env['s.order.history.points'].sudo().create([data_points])
                # khong lay bill
                if res.is_bill:
                    self.env['s.order.history.points'].sudo().create([{
                        'order_id': res.id,
                        'diem_cong': res.session_id.config_id.diem_khong_lay_bill,
                        'ly_do': 'Không lấy bill',
                        'res_partner_id': res.partner_id.id,
                        'is_bill':True,
                    }])
                    res.loyalty_points += res.session_id.config_id.diem_khong_lay_bill
            except Exception as e:
                self.env['ir.logging'].sudo().create({
                    'name': 'POS Order - s.order.history.points',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': str(e),
                    'func': 'Create - s.order.history.points',
                    'line': '0',
                })
            if res.lines:
                for line in res.lines:
                    if line.gift_card_id:
                        line.sudo().write({
                            'full_product_name': 'Gift Card - ' + line.gift_card_id.code,
                        })
        return res

    def update_gift_card_id(self):
        for rec in self:
            for line in rec.lines:
                if line.gift_card_id:
                    line.sudo().write({
                        'full_product_name': 'Gift Card - ' + line.gift_card_id.code,
                    })

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        return {
            'amount': ui_paymentline['amount'] or 0.0,
            'payment_date': ui_paymentline['name'],
            'payment_method_id': ui_paymentline['payment_method_id'],
            'card_type': ui_paymentline.get('card_type'),
            'cardholder_name': ui_paymentline.get('cardholder_name'),
            'transaction_id': ui_paymentline.get('transaction_id'),
            'payment_status': ui_paymentline.get('payment_status'),
            'payment_note': ui_paymentline.get('payment_note'),
            'ticket': ui_paymentline.get('ticket'),
            'pos_order_id': order.id,
            's_gift_card_id': ui_paymentline.get('s_gift_card_id'),
        }

    @api.model
    def create_from_ui(self, orders, draft=False):
        order_duplicate_ids = []
        for order in orders:
            create_s_lost_bill = False
            try:
                if 'server_id' in order['data']:
                    existing_order = self.env['pos.order'].search(
                        ['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])],
                        limit=1)
                    if len(existing_order) > 0:
                        if 'partner_id' in order['data']:
                            if existing_order.partner_id.id != order['data']['partner_id']:
                                #order da tao
                                name = order['data']['name']
                                order['data']['name'] = name + '-' + existing_order.date_order.strftime("%d-%m")
                                s_lost_bill_new = self.env['s.lost.bill'].sudo().create({
                                    'name': order['data']['name'],
                                    'amount_paid': order['data']['amount_paid'],
                                    'amount_total': order['data']['amount_total'],
                                    'amount_tax': order['data']['amount_tax'],
                                    'amount_return': order['data']['amount_return'],
                                    'creation_date': (fields.datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M"),
                                    'sale_person_id': order['data']['sale_person_id'],
                                    'partner_id': order['data']['partner_id'],
                                    'employee_id': order['data']['employee_id'],
                                    'pos_session_id': order['data']['pos_session_id'],
                                    'pricelist_id': order['data']['pricelist_id'],
                                    # 'to_invoice': order['data']['to_invoice'],
                                    # 'to_ship': order['data']['to_ship'],
                                    # 'is_tipped': order['data']['is_tipped'],
                                    # 'tip_amount': order['data']['tip_amount'],
                                    # 'loyalty_points': order['data']['loyalty_points'],
                                    'lines': order['data']['lines'],
                                    'statement_ids': order['data']['statement_ids'],
                                    'state': 'order_da_tao',
                                })
                                if s_lost_bill_new:
                                    create_s_lost_bill = True
            except Exception as e:
                # order loi
                existing_order = self.env['pos.order'].search(
                    [('pos_reference', '=', order['data']['name'])],
                    limit=1)
                if len(existing_order) > 0:
                    if 'partner_id' in order['data']:
                        if existing_order.partner_id.id != order['data']['partner_id']:
                            # order da tao
                            name = order['data']['name']
                            order['data']['name'] = name + '-' + existing_order.date_order.strftime("%d-%m")
                            self.env['s.lost.bill'].sudo().create({
                                'name': order['data']['name'],
                                'amount_paid': order['data']['amount_paid'],
                                'amount_total': order['data']['amount_total'],
                                'amount_tax': order['data']['amount_tax'],
                                'amount_return': order['data']['amount_return'],
                                'creation_date': (fields.datetime.now() + timedelta(hours=7)).strftime(
                                    "%Y-%m-%d %H:%M"),
                                'sale_person_id': order['data']['sale_person_id'],
                                'partner_id': order['data']['partner_id'],
                                'employee_id': order['data']['employee_id'],
                                'pos_session_id': order['data']['pos_session_id'],
                                'pricelist_id': order['data']['pricelist_id'],
                                'lines': order['data']['lines'],
                                'statement_ids': order['data']['statement_ids'],
                                'state': 'order_loi',
                            })
                self.env['ir.logging'].sudo().create({
                    'type': 'server',
                    'name': 'pos_order_create_from_ui',
                    'path': 'path',
                    'line': 'line',
                    'func': str(e),
                    'message': json.dumps(order)
                })
            if 'server_id' in order['data'] and not create_s_lost_bill:
                existing_order = self.env['pos.order'].search(
                    ['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])],
                    limit=1)
                if len(existing_order) > 0:
                    # order da ton tai
                    if 'partner_id' in order['data']:
                        if existing_order.partner_id.id != order['data']['partner_id']:
                            # Da tao order
                            name = order['data']['name']
                            order['data']['name'] = name + '-' + existing_order.date_order.strftime("%d-%m")
                            self.env['s.lost.bill'].sudo().create({
                                'name': order['data']['name'],
                                'amount_paid': order['data']['amount_paid'],
                                'amount_total': order['data']['amount_total'],
                                'amount_tax': order['data']['amount_tax'],
                                'amount_return': order['data']['amount_return'],
                                'creation_date': (fields.datetime.now() + timedelta(hours=7)).strftime(
                                    "%Y-%m-%d %H:%M"),
                                'sale_person_id': order['data']['sale_person_id'],
                                'partner_id': order['data']['partner_id'],
                                'employee_id': order['data']['employee_id'],
                                'pos_session_id': order['data']['pos_session_id'],
                                'pricelist_id': order['data']['pricelist_id'],
                                'lines': order['data']['lines'],
                                'statement_ids': order['data']['statement_ids'],
                                'state': 'order_da_ton_tai',
                            })
                        else:
                            self.env['s.lost.bill'].sudo().create({
                                'name': order['data']['name'],
                                'amount_paid': order['data']['amount_paid'],
                                'amount_total': order['data']['amount_total'],
                                'amount_tax': order['data']['amount_tax'],
                                'amount_return': order['data']['amount_return'],
                                'creation_date': (fields.datetime.now() + timedelta(hours=7)).strftime(
                                    "%Y-%m-%d %H:%M"),
                                'sale_person_id': order['data']['sale_person_id'],
                                'partner_id': order['data']['partner_id'],
                                'employee_id': order['data']['employee_id'],
                                'pos_session_id': order['data']['pos_session_id'],
                                'pricelist_id': order['data']['pricelist_id'],
                                'lines': order['data']['lines'],
                                'statement_ids': order['data']['statement_ids'],
                                'state': 'order_can_kiem_tra_lai',
                            })
                    self.env['ir.logging'].sudo().create({
                        'type': 'server',
                        'name': 'pos_order_create_from_ui',
                        'path': 'path',
                        'line': 'line',
                        'func': 'existing order: ' + str(existing_order.id),
                        'message': json.dumps(order)
                    })
            for order_id in orders:
                if order['data']['partner_id'] == order_id['data']['partner_id'] and order['data']['pos_session_id'] == order_id['data']['pos_session_id'] and order['id'] != order_id['id']:
                    if not order_duplicate_ids:
                        order_duplicate_ids.append(order)
                    elif order not in order_duplicate_ids:
                        order_duplicate_ids.append(order)
        if len(order_duplicate_ids) > 0:
            for order_duplicate_id in order_duplicate_ids:
                order_duplicate_id['data']['is_order_duplicate'] = True
                for r in order_duplicate_ids:
                    if order_duplicate_id['id'] != r['id'] and not order_duplicate_id['data'].get('order_duplicate_origin'):
                        order_duplicate_id['data']['order_duplicate_origin'] = r['data']['name']
        return super(SPosOrderInherit, self).create_from_ui(orders, draft)

    def force_update_return_sale_order_line_reward(self):
        for rec in self:
            for line in rec.lines:
                if line.price_unit < 0 and line.qty < 0 and not line.is_program_reward and not line.program_id and line.refunded_orderline_id:
                    if line.refunded_orderline_id.is_program_reward and line.refunded_orderline_id.program_id:
                        line.sudo().write({
                            'is_program_reward': True,
                            'program_id': line.refunded_orderline_id.program_id.id,
                        })

    def action_pos_order_paid(self):
        res = super(SPosOrderInherit, self).action_pos_order_paid()
        if self.state in ('paid', 'done', 'invoiced') and self.is_cancel_order == True:
            self.update({
                'pos_order_status': 'hoan_thanh'
            })
        return res

    def get_report_info_pos_order(self, domain=False):
        data_pos_order = []
        #get order cua customer
        query_pos_order = self._cr.execute("""select id,CAST( (date_order) AS Date ),pos_reference,total_quantity_pos,amount_paid,pos_name,sale_person_id from pos_order where partner_id = %s ORDER BY date_order DESC""",((domain),))
        result_query_pos_order = self._cr.dictfetchall()
        if result_query_pos_order:
            for order in result_query_pos_order:
                sale_person = self.env['hr.employee'].sudo().search([('id', '=', order.get('sale_person_id'))]).name
                vals = {
                    'date_order': order.get('date_order'),
                    'pos_reference': order.get('pos_reference'),
                    'total_quantity_pos': order.get('total_quantity_pos'),
                    'amount_paid': order.get('amount_paid'),
                    'pos_name': order.get('pos_name'),
                    'sale_person': sale_person,
                }
                details_product = self.format_details_product(order)
                if details_product:
                    vals.update({
                        'details_product': details_product
                    })
                    data_pos_order.append(vals)
        brand_total = []
        pos_order_ids = list(set([order['id'] for order in result_query_pos_order]))
        if pos_order_ids:
            query_product_in_lines = self._cr.execute("""select product_id from pos_order_line where order_id in %s""", (tuple(pos_order_ids),))
            product_product_ids = [product[0] for product in self._cr.fetchall()]
            query_brand = self._cr.execute("""select id from s_product_brand where id in 
            (select thuong_hieu from product_template where id in (select product_tmpl_id from product_product WHERE id in %s))""", (tuple(product_product_ids),))
            result_query_brand_ids = [res[0] for res in self._cr.fetchall()]
            if result_query_brand_ids:
                for brand in result_query_brand_ids:
                    query_brand_categ = self._cr.execute(
                                """SELECT count(pt.id), b.name as brand_name, c.name as categ_name FROM product_template as pt
                                FULL OUTER JOIN s_product_brand as b ON pt.thuong_hieu = b.id
                                FULL OUTER JOIN product_category as c ON pt.categ_id = c.id
                                WHERE pt.detailed_type = 'product'
                                            AND pt.id in (select product_tmpl_id from product_product WHERE id in %s)
                                            AND pt.thuong_hieu = %s GROUP BY b.name, c.name;
                                                """, (tuple(product_product_ids),(brand)))
                    result_query_brand_categ = [brand for brand in self._cr.dictfetchall()]
                    group_brand = {
                        'brand_name': result_query_brand_categ[0].get('brand_name'),
                        'total': sum([(r['count']) for r in result_query_brand_categ]),
                        'categ_list': result_query_brand_categ
                    }
                    brand_total.append(group_brand)
        return data_pos_order, brand_total

    def format_details_product(self, pos_order):
        res = []
        # order_lines = self.env['pos.order.line'].sudo().search([('order_id', '=', pos_order.get('id'))])

        # Tìm kiếm những dòng đơn hàng không phải là Giftcard, Chương trình khuyến mãi
        order_lines = self.env['pos.order.line'].sudo().search([('order_id', '=', pos_order.get('id')),
                                                                ('program_id', '=', False),
                                                                ('gift_card_id', '=', False)])
        if order_lines:
            for line in order_lines:
                vals = {
                    'sku': line.product_id.default_code,
                    'name': line.product_id.name,
                    'color': line.product_id.mau_sac if line.product_id.mau_sac else '',
                    'size': line.product_id.kich_thuoc if line.product_id.kich_thuoc else '',
                    'lst_price': line.product_id.lst_price,
                }
                res.append(vals)
        return res

    def _unlink_duplicate_promotion_program(self):
        for rec in self:
            promo_program = []
            list_ids = []
            for program in rec.applied_program_ids:
                pos_order_line_ids = program.pos_order_line_ids
                if pos_order_line_ids:
                    order_line_program = pos_order_line_ids.filtered(lambda r: r.order_id.id == rec.id)
                    if len(order_line_program):
                        vals = {
                            'chuong_trinh': program.name,
                            'id': program.id
                        }
                        if len(vals):
                            promo_program.append(vals)
                            list_ids.append(program.id)
            if len(promo_program):
                order = {
                    'id_don_hang': rec.id,
                    'don_hang': rec.pos_reference,
                    'chuong_trinh_ap_dung': promo_program,
                    'list_ids_chuong_trinh_ap_dung': list_ids
                }

    # def _compute_s_history_loyalty_point_po(self):
    #     for r in self:
    #         if r.partner_id:
    #             if r.partner_id.history_points_ids:
    #                 for history in r.partner_id.history_points_ids:
    #                     if history.order_id:
    #                         if history.order_id.id not in r.partner_id.pos_order_ids.mapped('id'):
    #                             history.unlink()
    #
    #                 history_loyalty_point_po_id = r.partner_id.history_points_ids.filtered(lambda p: p.order_id.id == r.id)
    #                 if not history_loyalty_point_po_id:
    #                     vals = {
    #                         'order_id': r.id,
    #                         'res_partner_id': r.partner_id.id,
    #                         'ly_do': 'Điểm trên đơn hàng ' + str(r.name),
    #                         'diem_cong': float(r.loyalty_points)
    #                     }
    #                     r.partner_id.history_points_ids = [(0, 0, vals)]

    def search_order(self, order_name):
        context = dict.fromkeys(['sale_person', 'customer_name', 'customer_phone', 'date_order'])
        pos_reference = self.env['pos.order'].sudo().search([('pos_reference', '=', order_name)], limit=1)
        if len(pos_reference) > 0:
            context['sale_person'] = pos_reference.sale_person_id.name
            context['customer_name'] = pos_reference.partner_id.name
            context['customer_phone'] = pos_reference.partner_id.phone
            user_tz = self.env.user.tz or pytz.utc
            tz = pytz.utc.localize(pos_reference.date_order).astimezone(pytz.timezone(user_tz))
            context['date_order'] = datetime.strftime(tz, "%d-%m-%Y %H:%M:%S")
        return context

    def _cron_compute_applied_program_ids(self):
        pos_order_ids = self.search([('applied_promotion_program', '!=', None)])
        for r in pos_order_ids:
            if r.applied_promotion_program:
                coupon_program_names = r.applied_promotion_program.split(',')
                for coupon_program_name in coupon_program_names:
                    coupon_program_id = self.env['coupon.program'].search([('name', '=', coupon_program_name)], limit=1)
                    if coupon_program_id:
                        if not r.applied_program_ids or coupon_program_id.id not in r.applied_program_ids.mapped('id'):
                            self.env['ir.logging'].sudo().create({
                                'name': '_cron_compute_applied_program_ids',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'INFO',
                                'path': 'url',
                                'message': 'POS Order chưa có liên kết CTKM: ' + r.name,
                                'func': '_compute_write_date_pos_order_line',
                                'line': '0',
                            })
                            r.applied_program_ids += coupon_program_id
                    self._cr.execute(
                        """UPDATE pos_order SET is_compute_coupon_program = True WHERE id = %s""",
                        (r.id,))

    def validate_coupon_programs(self, program_ids_to_generate_coupons, unused_coupon_ids):
        res = super(SPosOrderInherit, self).validate_coupon_programs(program_ids_to_generate_coupons, unused_coupon_ids)
        for r in res:
            boo_code = self.env['coupon.coupon'].sudo().search([('program_id', 'in', program_ids_to_generate_coupons), ('code', '=', r.get('code'))]).boo_code
            if boo_code:
                r.update({
                    'code': boo_code
                })
        return res

class SReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def s_get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        date_start = datetime.strptime(date_start, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)
        date_stop = datetime.strptime(date_stop, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)
        orders = self.env['pos.order'].sudo().search([('config_id', 'in', config_ids),
                                                      ('date_order', '>=', date_start),
                                                      ('date_order', '<=', date_stop)])
        s_bill_counter = 0
        s_return_order_revenue = 0
        s_order_revenue = 0
        s_net_revenue = 0
        payment_method_counter = []
        currency = '{:20,.2f}'
        pos = []
        for config_id in config_ids:
            pos_config = self.env['pos.config'].sudo().search([('id', '=', config_id)])
            if len(pos_config) > 0:
                pos.append(pos_config.name)
        for order in orders:
            if order.date_order >= date_start and order.date_order <= date_stop:
                s_bill_counter += 1
                for line in order.lines:
                    if (line.product_id.type == 'product' and line.price_subtotal_incl < 0) or (
                            line.product_id.type == 'service' and line.price_subtotal_incl > 0):
                        s_return_order_revenue += line.price_subtotal_incl
                    if (line.product_id.type == 'product' and line.price_subtotal_incl > 0) or (
                            line.product_id.type == 'service' and line.price_subtotal_incl < 0):
                        s_order_revenue += line.price_subtotal_incl
                    s_net_revenue = s_order_revenue - abs(s_return_order_revenue)
        pos_payment_method_ids = self.env['pos.payment.method'].sudo().search([])
        for pos_payment_method_id in pos_payment_method_ids:
            s_payment_method_counter = 0
            payment_orders = self.env['pos.payment'].sudo().search(
                [('payment_method_id', '=', pos_payment_method_id.id), ('session_id.config_id', 'in', config_ids)])
            for order in payment_orders:
                if order.pos_order_id.date_order >= date_start and order.pos_order_id.date_order <= date_stop:
                    s_payment_method_counter += order.amount
            if s_payment_method_counter != 0:
                payment_method_counter.append({
                    'payment_method': pos_payment_method_id.name,
                    'amount': currency.format(s_payment_method_counter)
                })

        report_data = {
            's_bill_counter': s_bill_counter,
            's_return_order_revenue': currency.format(s_return_order_revenue),
            's_order_revenue': currency.format(s_order_revenue),
            's_net_revenue': currency.format(s_net_revenue),
            's_payment_method_counter': payment_method_counter,
            'pos': (', ').join(pos)
        }
        return report_data

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        configs = self.env['pos.config'].browse(data['config_ids'])
        data.update(self.s_get_sale_details(data['date_start'], data['date_stop'], configs.ids))
        return data
