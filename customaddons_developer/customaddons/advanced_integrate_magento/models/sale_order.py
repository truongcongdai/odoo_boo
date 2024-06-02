from odoo import _, api, models, fields, SUPERUSER_ID
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = ['sale.order']

    payment_method = fields.Selection(
        selection=[
            ('cod', 'COD'),
            ('online', 'Online Payment')
        ],
        string='Payment Method',
    )
    customer_pickup_date = fields.Datetime(
        string='Customer Pickup Date'
    )
    coupon_code = fields.Char('Coupon Code')
    s_promo_code = fields.Char('Promo Code', readonly=True)
    gift_card_code = fields.Char('Gift card Code')
    gift_card_discount_amount = fields.Float('Gift card Code')
    loyalty_points = fields.Float(
        string='Loyalty points',
        required=False)
    loyalty_used_m2 = fields.Float(
        string='Loyalty used m2')
    m2_so_id = fields.Char('Magento ID')
    s_carrier_id = fields.Many2one('delivery.carrier', string="Shipping Method")
    shipment_status_date = fields.Datetime(
        string='Ngày giao hàng thành công/thất bại',
        compute='_compute_picking_ids_shipment_status',
        store=True
    )
    completed_date = fields.Datetime(string='Ngày hoàn thành đơn hàng', compute='_compute_stock_picking_date_done',
                                     store=True)
    sale_order_status = fields.Selection([
        ('moi', 'Mới'),
        ('dang_xu_ly', 'Đang xử lý'),
        ('dang_giao_hang', 'Đang giao hàng'),
        ('dang_chuyen_hoan', 'Đang chuyển hoàn'),
        ('da_giao_hang', 'Hoàn thành'),
        ('hoan_thanh_1_phan', 'Hoàn thành 1 phần'),
        ('hoan_thanh', 'Hoàn thành'),
        ('giao_hang_that_bai', 'Đơn hoàn'),
        ('huy', 'Hủy'),
        ('closed', 'Closed'),
    ], string='Tình trạng đơn hàng', default='moi', tracking=True, compute="_compute_sale_order_state", store=True)
    is_done_do = fields.Boolean(string='Là đơn hàng có DO hoàn thành', compute='_compute_picking_ids_done_do',
                                store=True)
    s_phone_m2 = fields.Char(string='Số điện thoại', related='partner_id.phone', groups="advanced_sale.s_boo_group_administration,advanced_sale.s_boo_group_ecom,advanced_sale.s_boo_group_area_manager,advanced_sale.s_boo_group_hang_hoa,advanced_sale.s_boo_group_dieu_phoi,advanced_sale.s_boo_group_ke_toan")

    # s_promo_program_m2 = fields.Char(compute='_compute_program_so_m2', string='Chương trình khuyến mãi', store=True)
    check_so_report = fields.Boolean(default=False)

    # s_url_pod = fields.Boolean(string='URL POD', default=False)
    s_url_pod = fields.Boolean(string='URL POD', default=False, compute='_compute_url_pod', store=True)

    @api.depends('order_line.pod_image_url')
    def _compute_url_pod(self):
        for rec in self:
            rec.s_url_pod = False
            if rec.order_line:
                for line in rec.order_line:
                    if line.pod_image_url:
                        rec.s_url_pod = True
                        break

    @api.depends('picking_ids.shipment_status')
    def _compute_picking_ids_shipment_status(self):
        for r in self:
            r.shipment_status_date = False
            stock_picking_ids = []
            if r.picking_ids and r.is_magento_order:
                for picking_id in r.picking_ids:
                    if picking_id.shipment_status:
                        stock_picking_ids.append(picking_id.id)
            if stock_picking_ids:
                stock_picking_ids.sort()
                stock_picking_id = r.picking_ids.filtered(lambda p: p.id == stock_picking_ids[-1])
                if stock_picking_id:
                    r.shipment_status_date = stock_picking_id.date_done

    # @api.depends('s_promo_code', 'coupon_code')
    # def _compute_program_so_m2(self):
    #     for rec in self:
    #         rec.s_promo_program_m2 = ''
    #         if rec.s_promo_code and not rec.coupon_code:
    #             promo_code = self.env['coupon.program'].sudo().search([('ma_ctkm', '=', rec.s_promo_code)])
    #             if len(promo_code) > 0:
    #                 rec.s_promo_program_m2 = promo_code.name
    #         elif rec.coupon_code and not rec.s_promo_code:
    #             coupon_code = self.env['coupon.coupon'].sudo().search([('boo_code', '=', rec.coupon_code)])
    #             if len(coupon_code) > 0:
    #                 rec.s_promo_program_m2 = coupon_code.program_id.name
    #         else:
    #             split_promo_code = ''
    #             if rec.s_promo_code:
    #                 split_promo_code = rec.s_promo_code.split(',')
    #             if len(split_promo_code) > 0:
    #                 ### Trường hợp áp dụng nhiều CTKM
    #                 coupon_code = self.env['coupon.coupon'].sudo().search([('boo_code', '=', rec.coupon_code)])
    #                 if len(coupon_code) > 0:
    #                     rec.s_promo_program_m2 = coupon_code.program_id.name + ', '
    #                 list_promo_code = rec.s_promo_code.split(',')
    #                 for e in list_promo_code:
    #                     promo_code = self.env['coupon.program'].sudo().search([('ma_ctkm', '=', e)])
    #                     if len(promo_code) > 0:
    #                         rec.s_promo_program_m2 += promo_code.name + ', '
    #             else:
    #                 promo_code = self.env['coupon.program'].sudo().search([('ma_ctkm', '=', rec.s_promo_code)])
    #                 coupon_code = self.env['coupon.coupon'].sudo().search([('boo_code', '=', rec.coupon_code)])
    #                 if len(promo_code) > 0 and len(coupon_code) > 0:
    #                     rec.s_promo_program_m2 = promo_code.name + ', ' + coupon_code.program_id.name

    @api.depends('picking_ids.state')
    def _compute_picking_ids_done_do(self):
        for r in self:
            r.is_done_do = False
            if len(r.picking_ids):
                if 'done' in r.picking_ids.mapped('state'):
                    r.is_done_do = True

    @api.depends('picking_ids.state')
    def _compute_stock_picking_date_done(self):
        for rec in self:
            ###Trường hợp đơn marketplace khi ở trạng thái cuối -> có completed_date -> không update completed_date
            old_completed_date = rec.completed_date
            rec.completed_date = False
            if old_completed_date:
                rec.completed_date = old_completed_date
            picking_ids_state = rec.picking_ids.mapped('state')
            if (not rec.is_magento_order and not rec.is_ecommerce_order) or (rec.is_ecommerce_order and rec.return_order_id):
                if rec.picking_ids and len(rec.picking_ids.filtered(lambda sp: sp.state == 'done')) == len(
                        rec.picking_ids) \
                        or 'done' in picking_ids_state \
                        and 'cancel' in picking_ids_state \
                        and 'draft' not in picking_ids_state \
                        and 'waiting' not in picking_ids_state \
                        and 'confirmed' not in picking_ids_state \
                        and 'assigned' not in picking_ids_state:
                    list_date_done = rec.picking_ids.filtered(lambda p: p.date_done is not False).mapped('date_done')
                    if len(list_date_done) > 0:
                        rec.completed_date = max(list_date_done)

    def create_invoices_via_api_calling(self, data):
        self.ensure_one()
        if self.invoice_ids:
            for order_invoice_id in self.invoice_ids:
                if order_invoice_id.state != 'posted':
                    order_invoice_id.sudo().action_post()
        if self.payment_method == 'online':
            account_move_obj = self.env['account.move'].with_user(SUPERUSER_ID)
            default_sale_journal_id = account_move_obj._search_default_journal(['sale']).id
            invoice_data = {
                'partner_id': self.partner_id.id,
                'payment_method': 'cod',
                'journal_id': default_sale_journal_id,
                'move_type': 'out_invoice',
                'state': 'draft',
                'invoice_line_ids': [(0, 0, {
                    'journal_id': default_sale_journal_id,
                    'partner_id': self.partner_id.commercial_partner_id.id,
                    'currency_id': self.env.company.currency_id.id,
                    'product_id': order_line_id.product_id.id,
                    'quantity': order_line_id.product_uom_qty,
                    'm2_total_line_discount': (
                                                      order_line_id.m2_total_line_discount * order_line_id.qty_delivered / order_line_id.product_uom_qty) / order_line_id.product_uom_qty if order_line_id.product_uom_qty > 0 else 0,
                    'tax_ids': [(6, 0, order_line_id.tax_id.ids)],
                    'price_unit': order_line_id.price_unit,
                    'sale_line_ids': [(6, 0, order_line_id.ids)]
                }) for order_line_id in self.order_line]
            }

            invoice = account_move_obj.create(invoice_data)
            gift_card_line_so = self.order_line.filtered(lambda l: l.product_id.detailed_type == 'gift')
            if gift_card_line_so:
                if gift_card_line_so.product_id.id not in invoice.line_ids.mapped('product_id.id'):
                    invoice.invoice_line_ids = [(0, 0, {
                        'product_id': gift_card_line_so.product_id.id,
                        'quantity': 1,
                        'price_unit': gift_card_line_so.price_unit
                    })]
            if self.s_carrier_id:
                product_order_line = self.env['sale.order.line'].sudo().search([
                    ('order_id', '=', self.id),
                    ('product_id', '=', self.s_carrier_id.product_id.id)
                ])
                if product_order_line:
                    product_order_line.write({
                        'invoice_status': 'invoiced'
                    })
            if invoice:
                invoice.sudo().action_post()
                invoice.sudo().action_direct_register_payment()
        if self.payment_method == 'cod':
            account_move_obj = self.env['account.move'].with_user(SUPERUSER_ID)
            account_magento_id = account_move_obj.search([('magento_do_id', '=', data.get('magento_do_id'))])
            if account_magento_id:
                raise ValidationError('Invoice already exists!')
            default_sale_journal_id = account_move_obj._search_default_journal(['sale']).id
            confirm_deliveries = self.picking_ids.filtered(
                lambda
                    rec: rec.location_dest_id.usage == 'customer' and rec.state == 'done' and rec.magento_do_id == data.get(
                    'magento_do_id')
            )
            create_invoice_data = []
            i = 0
            for pick in confirm_deliveries:
                i += 1
                if i > 1 and self.s_carrier_id:
                    line_carrier_id = pick.move_ids_without_package.filtered(
                        lambda l: l.product_id.id == self.s_carrier_id.product_id.id)
                    if line_carrier_id:
                        pick.move_ids_without_package = pick.move_ids_without_package - line_carrier_id
                invoice_line_ids = []

                for move in pick.move_ids_without_package:
                    invoice_line_ids.append({
                        'journal_id': default_sale_journal_id,
                        'partner_id': pick.partner_id.commercial_partner_id.id,
                        'currency_id': self.env.company.currency_id.id,
                        'product_id': move.product_id.id,
                        'quantity': move.product_uom_qty,
                        'tax_ids': [(6, 0, move.sale_line_id.tax_id.ids)],
                        'm2_total_line_discount': (
                                                              move.sale_line_id.m2_total_line_discount * move.sale_line_id.qty_delivered / move.sale_line_id.product_uom_qty) / move.product_uom_qty if move.product_uom_qty > 0 else 0,
                        'price_unit': move.sale_line_id.price_unit,
                        'sale_line_ids': [(6, 0, move.sale_line_id.ids)]
                    })
                    if move.is_product_free:
                        invoice_line_ids.append({
                            'journal_id': default_sale_journal_id,
                            'partner_id': pick.partner_id.commercial_partner_id.id,
                            'currency_id': self.env.company.currency_id.id,
                            'product_id': move.product_id.id,
                            'quantity': move.product_uom_qty,
                            'tax_ids': [(6, 0, move.sale_line_id.tax_id.ids)],
                            'm2_total_line_discount': 0,
                            'price_unit': -move.sale_line_id.price_unit,
                            'sale_line_ids': [(6, 0, move.sale_line_id.ids)]
                        })
                invoice_data = {
                    'partner_id': pick.partner_id.id,
                    'magento_do_id': pick.magento_do_id if pick.magento_do_id else '',
                    'payment_method': 'cod',
                    'journal_id': default_sale_journal_id,
                    'move_type': 'out_invoice',
                    'state': 'draft',
                    'invoice_line_ids': invoice_line_ids
                }

                create_invoice_data.append(invoice_data)
            if create_invoice_data:
                account_move_new_value = account_move_obj.create(create_invoice_data)
                gift_card_line_so = self.order_line.filtered(lambda l: l.product_id.detailed_type == 'gift')
                if gift_card_line_so:
                    if gift_card_line_so.product_id.id not in account_move_new_value.line_ids.mapped('product_id.id'):
                        account_move_new_value.invoice_line_ids = [(0, 0, {
                            'product_id': gift_card_line_so.product_id.id,
                            'quantity': 1,
                            'price_unit': gift_card_line_so.price_unit
                        })]
                if self.s_carrier_id:
                    product_order_line = self.env['sale.order.line'].sudo().search([
                        ('order_id', '=', self.id),
                        ('product_id', '=', self.s_carrier_id.product_id.id)
                    ])
                    if product_order_line:
                        product_order_line.write({
                            'invoice_status': 'invoiced'
                        })
                cod_price_total_line = 0
                if account_move_new_value:
                    if account_move_new_value.invoice_line_ids:
                        for r in account_move_new_value.invoice_line_ids:
                            cod_price_total_line += r.price_subtotal
                        cod_amount = data.get('cod_amount', 0)
                        if cod_amount > cod_price_total_line:
                            product_old_value = self.env['product.product'].sudo().search([
                                ('la_so_tien_phai_thu_them', '=', True)
                            ], limit=1)
                            if product_old_value:
                                account_move_new_value.invoice_line_ids = [(0, 0, {
                                    'product_id': product_old_value.id,
                                    'quantity': 1,
                                    'price_unit': cod_amount - cod_price_total_line
                                })]
                            else:
                                product_new_value = self.env['product.product'].sudo().create({
                                    'name': 'Số tiền phải thu thêm',
                                    'detailed_type': 'service',
                                    'la_so_tien_phai_thu_them': True
                                })
                                account_move_new_value.invoice_line_ids = [(0, 0, {
                                    'product_id': product_new_value.id,
                                    'quantity': 1,
                                    'price_unit': cod_amount - cod_price_total_line
                                })]
                    account_move_new_value.sudo().action_post()
                    account_move_new_value.sudo().action_direct_register_payment()
        # return self.invoice_ids.sudo().action_post()

    # @api.depends('state')
    # def _compute_sale_order_state(self):
    #     for r in self:
    #         if r.state == 'draft' or r.state == 'sent':
    #             r.sale_order_status = 'moi'
    #         if r.state == 'done':
    #             r.sale_order_status = 'hoan_thanh'
    #         if r.state == 'sale':
    #             r.sale_order_status = 'dang_xu_ly'
    #         if r.state == 'cancel':
    #             r.sale_order_status = 'huy'

    def _loyalty_point_so(self):
        for rec in self:
            s_order_history_point = self.env['s.order.history.points'].sudo()
            s_order_history_point_id = s_order_history_point.search([('sale_order_id', '=', rec.id)])

            loyalty_points = 0
            s_so_loyalty_points_id = self.env['s.sale.order.loyalty.program'].sudo().search(
                [('is_sale_order', '=', True)], limit=1)
            if s_so_loyalty_points_id:
                for order_line in rec.order_line:
                    if order_line.qty_delivered and order_line.product_id.type == 'product':
                        # diem = (don_gia * da_giao) - ((tong_chiet_khau / so_luong) * da_giao) = da_giao * (don_gia - (tong_chiet_khau/so_luong))
                        loyalty_points += round(order_line.qty_delivered * (order_line.price_unit - (
                                order_line.m2_total_line_discount / order_line.product_uom_qty)) * float(
                            s_so_loyalty_points_id.s_points_currency), 6)
            if len(s_order_history_point_id) == 0:
                rec.loyalty_points += loyalty_points - rec.loyalty_used_m2
                rec.partner_id.write({
                    'loyalty_points': rec.partner_id.loyalty_points + rec.loyalty_points
                })
                self.env['s.order.history.points'].sudo().create([{
                    'sale_order_id': rec.id,
                    'ly_do': 'Điểm trên đơn hàng ' + rec.name,
                    'diem_cong': rec.loyalty_points,
                    'res_partner_id': rec.partner_id.id
                }])
                return loyalty_points
            # else:
            #     s_order_history_point_id.sudo().write({
            #         'diem_cong': loyalty_points,
            #     })
            #     return loyalty_points


    # @api.depends('sale_order_status')
    # def _compute_sale_order_status(self):
    #     for rec in self:
    #         rec.loyalty_points = 0
    # if rec.sale_order_status == 'hoan_thanh_1_phan' or rec.sale_order_status == 'hoan_thanh' and rec.partner_id:
    # if rec.sale_order_status == 'hoan_thanh' and rec.partner_id:
    #     rec.loyalty_points = self._loyalty_point_so()
    # if rec.sale_order_status == 'hoan_thanh_1_phan':
    #     picking_ids = rec.picking_ids.filtered(lambda p: p.state in ['assigned', 'waiting'])
    #     if len(picking_ids) == 0:
    #         rec.loyalty_points = self._loyalty_point_so()
    # else:
    #     rec.loyalty_points = self._loyalty_point_so()

    @api.depends('state', 'picking_ids.state')
    def _compute_sale_order_state(self):
        for rec in self:
            if rec.is_magento_order and rec.sale_order_status == 'hoan_thanh_1_phan':
                if len(rec.picking_ids) > 0:
                    picking_ids = rec.picking_ids.filtered(
                        lambda p: p.state in ['draft', 'confirmed', 'assigned', 'waiting'])
                    # if len(picking_ids) == 0:
                    #     rec.loyalty_points = self._loyalty_point_so()
            if (not rec.is_magento_order and not rec.is_ecommerce_order) or (rec.is_ecommerce_order and rec.return_order_id):
                # if rec.partner_id and rec.state == 'sale':
                #     rec.loyalty_points = self._loyalty_point_so()
                if len(rec.picking_ids) > 0:
                    picking_state = list(set([picking.state for picking in rec.picking_ids]))
                    if len(picking_state) > 1:
                        if 'waiting' in picking_state or 'confirmed' in picking_state or 'assigned' in picking_state:
                            if rec.sale_order_status not in ['hoan_thanh_1_phan', 'hoan_thanh']:
                                # rec.sudo().sale_order_status = 'dang_xu_ly'
                                rec.sudo().write({
                                    'sale_order_status': 'dang_xu_ly'
                                })
                            # rec.sudo().sale_order_status = 'dang_xu_ly'
                        elif 'done' not in picking_state:
                            rec.sudo().write({
                                'sale_order_status': 'huy'
                            })
                            # rec.sudo().sale_order_status = 'huy'
                        else:
                            rec.sudo().write({
                                'sale_order_status': 'hoan_thanh'
                            })
                            # rec.sudo().sale_order_status = 'hoan_thanh'
                    else:
                        if 'draft' in picking_state:
                            rec.sudo().write({
                                'sale_order_status': 'moi'
                            })
                            # rec.sudo().sale_order_status = 'moi'
                        elif 'done' in picking_state:
                            rec.sudo().write({
                                'sale_order_status': 'hoan_thanh'
                            })
                            # rec.sudo().sale_order_status = 'hoan_thanh'
                        elif 'cancel' in picking_state:
                            rec.sudo().write({
                                'sale_order_status': 'huy'
                            })
                            # rec.sudo().sale_order_status = 'huy'
                        else:
                            rec.sudo().write({
                                'sale_order_status': 'dang_xu_ly'
                            })
                            # rec.sudo().sale_order_status = 'dang_xu_ly'
                else:
                    if rec.state in ['draft', 'sent']:
                        rec.sudo().write({
                            'sale_order_status': 'moi'
                        })
                        # rec.sudo().sale_order_status = 'moi'
                    elif rec.state in ['sale']:
                        rec.sudo().write({
                            'sale_order_status': 'dang_xu_ly'
                        })
                    elif rec.state in ['done']:
                        rec.sudo().write({
                            'sale_order_status': 'hoan_thanh'
                        })
                        # rec.sudo().sale_order_status = 'hoan_thanh'
                    else:
                        rec.sudo().write({
                            'sale_order_status': 'huy'
                        })
                        # rec.sudo().sale_order_status = 'huy'

    def select_update_sale_order_status(self):
        self._compute_sale_order_state()

    # def write(self, vals):
        # if vals.get('sale_order_status', '') == 'hoan_thanh' or vals.get('sale_order_status',
        #                                                                  '') == 'hoan_thanh_1_phan':
        #     self.loyalty_points = self._loyalty_point_so()
        # if vals.get('state', '') == 'cancel':
        #     self.calculate_reward_points_with_edit_order(vals)
        # return super(SaleOrder, self).write(vals)

    # def calculate_reward_points_with_create_order(self, vals):
    #     for r in self:
    #         # Tinh diem loyalty_points cua customer khi tao moi order
    #         if vals.get('state', '') == 'sale' and r.partner_id:
    #             total_loyalty_points = r.loyalty_points - r.loyalty_used_m2
    #             if total_loyalty_points:
    #                 r.partner_id.sudo().write({
    #                     'loyalty_points': r.partner_id.loyalty_points + total_loyalty_points
    #                 })
    #                 data_points = {
    #                     'diem_cong': total_loyalty_points,
    #                     'ly_do': 'Điểm trên đơn hàng Ecommerce',
    #                     'res_partner_id': r.partner_id.id
    #                 }
    #                 if self._name == 'sale.order':
    #                     data_points['sale_order_id'] = r.id
    #                 else:
    #                     data_points['order_id'] = r.id
    #                 self.env['s.order.history.points'].sudo().create([data_points])
    #             elif total_loyalty_points == 0:
    #                 r.partner_id.sudo().write({
    #                     'loyalty_points': r.partner_id.loyalty_points
    #                 })

    def calculate_reward_points_with_edit_order(self, vals):
        for r in self:
            # Tinh diem loyalty_points cua customer khi huy order
            if vals.get('state', '') == 'cancel' and r.partner_id:
                total_loyalty_points = r.loyalty_points - r.loyalty_used_m2
                if total_loyalty_points:
                    r.partner_id.sudo().write({
                        'loyalty_points': r.partner_id.loyalty_points - total_loyalty_points
                    })
                    self.env['s.order.history.points'].sudo().create([{
                        'order_id': r.id,
                        'diem_cong': total_loyalty_points,
                        'ly_do': 'Điểm trên đơn hàng Ecommerce',
                        'res_partner_id': r.partner_id.id
                    }])
                s_so_loyalty_points_id = self.env['s.sale.order.loyalty.program'].sudo().search([], limit=1)
                if s_so_loyalty_points_id:
                    loyalty_points = round(r.amount_total * float(s_so_loyalty_points_id.s_points_currency), 1)
                    r.partner_id.write({
                        'loyalty_points': r.partner_id.loyalty_points - loyalty_points
                    })
                    self.env['s.order.history.points'].sudo().create([{
                        'sale_order_id': r.id,
                        'ly_do': 'Đơn hàng ' + r.name + ' Hủy',
                        'diem_cong': -loyalty_points,
                        'res_partner_id': r.partner_id.id
                    }])

    def create_boo_api_procurement_group(self):
        self.ensure_one()
        procurement_group_obj = self.env['procurement.group']
        self_procurement_group = procurement_group_obj.search([('name', '=', self.name), ('sale_id', '=', self.id)])
        if not self_procurement_group:
            self_procurement_group = procurement_group_obj.create({
                'name': self.name,
                'move_type': self.picking_policy,
                'sale_id': self.id,
                'partner_id': self.partner_shipping_id.id,
            })
        self.write({'procurement_group_id': self_procurement_group.id})
        return self_procurement_group

    def cron_compute_s_history_loyalty_point(self):
        partner_ids = self.env['res.partner'].sudo().browse([])
        res_partner_so_magento_ids = self.sudo().read_group([('is_magento_order', '=', True)], ['partner_id'],
                                                            ['partner_id'])
        if res_partner_so_magento_ids:
            for res_partner_so_magento_id in res_partner_so_magento_ids:
                id_res_partner = res_partner_so_magento_id['partner_id'][0]
                if id_res_partner:
                    partner_id = self.env['res.partner'].search([('id', '=', id_res_partner)], limit=1)
                    if partner_id:
                        partner_ids += partner_id
        if len(partner_ids):
            self._compute_s_history_loyalty_point(partner_ids)

    def _compute_s_history_loyalty_point(self, vals):
        for r in vals:
            program_loyalty_point = self.env['s.sale.order.loyalty.program'].sudo().search([], limit=1)
            if program_loyalty_point:
                for sale_order_id in r.sale_order_ids:
                    diem_cong = sale_order_id.loyalty_points
                    loyalty_points = 0
                    if sale_order_id.sale_order_status in ['hoan_thanh_1_phan', 'hoan_thanh']:
                        for order_line in sale_order_id.order_line:
                            if order_line.product_id.detailed_type == 'product':
                                if order_line.qty_delivered == 0:
                                    pos_order_line_ids = order_line.pos_order_line_ids
                                    if pos_order_line_ids:
                                        for po in pos_order_line_ids:
                                            loyalty_points += round(
                                                po.price_unit * abs(po.qty) * float(
                                                    program_loyalty_point.s_points_currency), 6)
                                else:
                                    loyalty_points += round(
                                        (order_line.price_unit * order_line.qty_delivered -
                                         order_line.m2_total_line_discount) * float(
                                            program_loyalty_point.s_points_currency), 6)
                            else:
                                loyalty_points += round(order_line.price_total *
                                                        float(program_loyalty_point.s_points_currency), 6)
                    diem_cong += loyalty_points
                    if diem_cong:
                        vals_history = {
                            'sale_order_id': sale_order_id.id,
                            'res_partner_id': r.id,
                            'ly_do': 'Điểm trên đơn hàng ' + str(sale_order_id.name),
                            'diem_cong': float(diem_cong)
                        }
                        history_loyalty_point_ids = r.history_points_ids.filtered(
                            lambda l: l.sale_order_id.id == sale_order_id.id)
                        history_loyalty_point_so_ids = r.s_history_loyalty_point_so_ids.filtered(
                            lambda l: l.sale_order_id.id == sale_order_id.id)
                        if len(history_loyalty_point_ids) > 0:
                            if history_loyalty_point_ids[0].diem_cong != diem_cong:
                                r.sudo().write({
                                    'loyalty_points': r.loyalty_points - history_loyalty_point_ids[
                                        0].diem_cong + diem_cong
                                })
                                history_loyalty_point_ids[0].unlink()
                                if not history_loyalty_point_so_ids:
                                    self.env['s.history.loyalty.point.so'].sudo().create(vals_history)
                        elif len(history_loyalty_point_so_ids) > 0:
                            if history_loyalty_point_so_ids[0].diem_cong != diem_cong:
                                r.sudo().write({
                                    'loyalty_points': r.loyalty_points - history_loyalty_point_so_ids[
                                        0].diem_cong + diem_cong
                                })
                                history_loyalty_point_so_ids[0].sudo().write(vals_history)
                        else:
                            r.sudo().write({
                                'loyalty_points': r.loyalty_points + diem_cong
                            })
                            self.env['s.history.loyalty.point.so'].sudo().create(vals_history)
            # Start - Remove lịch sử tích điểm có điểm cộng = 0
            history_loyalty_point_zero_ids = r.history_points_ids.filtered(lambda h: h.diem_cong == 0)
            if history_loyalty_point_zero_ids:
                for rec in history_loyalty_point_zero_ids:
                    rec.unlink()
            history_loyalty_point_so_zero_ids = r.s_history_loyalty_point_so_ids.filtered(
                lambda h_so: h_so.diem_cong == 0)
            if history_loyalty_point_so_zero_ids:
                for rec in history_loyalty_point_so_zero_ids:
                    rec.unlink()
            # End - Remove lịch sử tích điểm có điểm cộng = 0
            # Start - Remove lịch sử tích điểm có trạng thái đơn hàng là Hủy
            # if r.s_history_loyalty_point_so_ids:
            #     for history_points_so_cancel in r.s_history_loyalty_point_so_ids:
            #         if history_points_so_cancel.sale_order_id.sale_order_status == 'huy':
            #             history_points_so_cancel.unlink()
            # if r.history_points_ids:
            #     for history_points_cancel in r.history_points_ids:
            #         if history_points_cancel.sale_order_id.sale_order_status == 'huy':
            #             history_points_cancel.unlink()
            # End - Remove lịch sử tích điểm có trạng thái đơn hàng là Hủy
            # Start - Lấy lịch sử tích điểm của KH type = delivery lưu sang lịch sử tích điểm của KH type = contact
            partner_delivery_ids = self.env['res.partner'].search([('parent_id', '=', r.id)])
            if partner_delivery_ids:
                for parner_delivery_id in partner_delivery_ids:
                    if parner_delivery_id.history_points_ids:
                        for parner_delivery_history_points_id in parner_delivery_id.history_points_ids:
                            if parner_delivery_history_points_id.sale_order_id.id not in r.history_points_ids.mapped(
                                    'sale_order_id.id') and parner_delivery_history_points_id.sale_order_id.id not in r.s_history_loyalty_point_so_ids.mapped(
                                'sale_order_id.id') and parner_delivery_history_points_id.sale_order_id.sale_order_status in [
                                'hoan_thanh', 'hoan_thanh_1_phan'] and parner_delivery_history_points_id.diem_cong:
                                r.s_history_loyalty_point_so_ids = [(0, 0, {
                                    'sale_order_id': parner_delivery_history_points_id.sale_order_id.id,
                                    'res_partner_id': r.id,
                                    'ly_do': 'Điểm trên đơn hàng ' + str(
                                        parner_delivery_history_points_id.sale_order_id.name),
                                    'diem_cong': float(parner_delivery_history_points_id.diem_cong)
                                })]
                                r.sudo().write({
                                    'loyalty_points': r.loyalty_points + parner_delivery_history_points_id.diem_cong
                                })
            # End - Lấy lịch sử tích điểm của KH type = delivery lưu sang lịch sử tích điểm của KH type = contact

    def cron_compute_sale_order_line_coupon_program(self):
        sale_order_magento_ids = self.sudo().search(['|', ('coupon_code', '!=', False), ('s_promo_code', '!=', False),
                                                     ('check_so_report', '=', False)])
        if sale_order_magento_ids:
            for sale_order_magento_id in sale_order_magento_ids:
                coupon_program_ids = []
                if sale_order_magento_id.coupon_code:
                    coupon_m2_ids = sale_order_magento_id.coupon_code.split(',')
                    if coupon_m2_ids:
                        for coupon_m2_id in coupon_m2_ids:
                            coupon_odoo = self.env['coupon.coupon'].search([
                                ('boo_code', '=', coupon_m2_id), ('state', '=', 'used'),
                                ('sales_order_id', '=', sale_order_magento_id.id)], limit=1)
                            if coupon_odoo and coupon_odoo.program_id:
                                coupon_program_price = 0
                                if coupon_odoo.program_id.reward_type == 'discount':
                                    if coupon_odoo.program_id.discount_type == 'fixed_amount':
                                        coupon_program_price = coupon_odoo.program_id.discount_fixed_amount
                                    elif coupon_odoo.program_id.discount_type == 'percentage' and coupon_odoo.program_id.discount_apply_on == 'on_order':
                                        coupon_program_price = sum(sale_order_magento_id.order_line.filtered(lambda l: not l.is_product_free and l.product_id.detailed_type == 'product').mapped('price_subtotal'))*coupon_odoo.program_id.discount_percentage/100
                                coupon_program_ids.append({
                                    'id': coupon_odoo.program_id.id,
                                    'name': coupon_odoo.program_id.name,
                                    'price': coupon_program_price
                                })
                if sale_order_magento_id.s_promo_code:
                    promo_m2_ids = sale_order_magento_id.s_promo_code.split(',')
                    if promo_m2_ids:
                        for promo_m2_id in promo_m2_ids:
                            promo_odoo = self.env['coupon.program'].search([('ma_ctkm', '=', promo_m2_id)], limit=1)
                            if promo_odoo:
                                coupon_program_price = 0
                                if promo_odoo.reward_type == 'discount':
                                    if promo_odoo.discount_type == 'fixed_amount':
                                        coupon_program_price = promo_odoo.discount_fixed_amount
                                    elif promo_odoo.discount_type == 'percentage' and promo_odoo.discount_apply_on == 'on_order':
                                        coupon_program_price = sum(sale_order_magento_id.order_line.filtered(lambda l: not l.is_product_free and l.product_id.detailed_type == 'product').mapped('price_subtotal')) * promo_odoo.discount_percentage / 100
                                coupon_program_ids.append({
                                    'id': promo_odoo.id,
                                    'name': promo_odoo.name,
                                    'price': coupon_program_price
                                })
                if coupon_program_ids:
                    for coupon_program_id in coupon_program_ids:
                        product_coupon_program = self.env['product.product'].sudo().search([
                            ('name', '=', coupon_program_id['name'])], limit=1)
                        if product_coupon_program:
                            product_id = product_coupon_program.id
                        else:
                            product_coupon_program = self.env['product.product'].sudo().create({
                                'name': coupon_program_id['name'],
                                'detailed_type': 'service',
                                'lst_price': coupon_program_id['price'],
                                'is_line_ctkm_m2': True
                            })
                            product_id = product_coupon_program.id
                        self.env['sale.order.line.coupon.program'].sudo().create({
                            'product_id': product_id,
                            'product_uom_qty': 1,
                            'price_total': coupon_program_id['price'],
                            'price_subtotal': coupon_program_id['price'],
                            'price_unit': coupon_program_id['price'],
                            'coupon_program_id': coupon_program_id['id'],
                            'program_name': coupon_program_id['name'],
                            'order_id': sale_order_magento_id.id,
                            'is_line_coupon_program': True,
                        })
                        applied_program_id = self.env['coupon.program'].browse(coupon_program_id['id'])
                        if applied_program_id:
                            sale_order_magento_id.applied_program_ids += applied_program_id
                self._cr.execute("""UPDATE sale_order SET check_so_report = True WHERE id = %s """,
                                 (sale_order_magento_id.id, ))

    def _cron_compute_source_id_so_m2(self):
        so_m2_ids = self.env['sale.order'].sudo().search([('is_magento_order', '=', True)])
        if so_m2_ids:
            self._action_compute_source_id_so_m2(so_m2_ids)
            for so_m2_id in so_m2_ids:
                so_m2_return_ids = self.sudo().search([('return_order_id', '=', so_m2_id.id)])
                if so_m2_return_ids:
                    self._action_compute_source_id_so_m2(so_m2_return_ids)

    def _action_compute_source_id_so_m2(self, so_m2_ids):
        for r in so_m2_ids:
            magento_source_id = self.env.ref('advanced_sale.utm_source_magento_order')
            if magento_source_id and not r.source_id:
                vals = (magento_source_id.id, r.id)
                self._cr.execute("""UPDATE sale_order SET source_id = %s WHERE id = %s """, vals)

    def check_discount_so_m2(self):
        order_error = []
        for r in self:
            total_amount_line = 0
            for line_id in r.order_line.filtered(lambda l: l.product_id.detailed_type == 'product' and l.product_uom_qty != 0):
                if line_id.order_id.date_order >= datetime.strptime('12/05/2023 00:00',
                                                                       '%d/%m/%Y %H:%M') and line_id.order_id.sale_order_status == 'hoan_thanh_1_phan':
                    product_uom_qty = line_id.qty_delivered
                else:
                    product_uom_qty = line_id.product_uom_qty
                if 0 <= line_id.price_unit < line_id.s_lst_price:
                    amount_line = product_uom_qty * line_id.s_lst_price
                else:
                    amount_line = product_uom_qty * line_id.price_unit

                discount_amount_line = 0
                if line_id.product_uom_qty < 0:
                    if line_id.order_id.is_magento_order:
                        discount_amount_line -= (
                                line_id.m2_total_line_discount + line_id.boo_total_discount)
                    else:
                        discount_amount_line -= (
                                line_id.boo_total_discount_percentage + line_id.boo_total_discount)
                else:
                    if line_id.order_id.is_magento_order:
                        discount_amount_line += line_id.m2_total_line_discount + line_id.boo_total_discount
                    else:
                        discount_amount_line += line_id.boo_total_discount_percentage + line_id.boo_total_discount
                if amount_line != 0:
                    total_amount_line += (amount_line - discount_amount_line)
            # Nếu đơn có phí ship M2
            line_ship_m2 = r.order_line.filtered(lambda l: l.product_id.la_phi_ship_hang_m2)
            if line_ship_m2:
                total_amount_line += line_ship_m2.price_total
            # Nếu đơn hoàn thành 1 phần
            if r.sale_order_status == 'hoan_thanh_1_phan':
                line_not_success_ids = r.order_line.filtered(
                    lambda l: l.qty_delivered == 0 and l.product_id.detailed_type == 'product')
                for line_not_success_id in line_not_success_ids:
                    total_amount_line += round(line_not_success_id.price_unit - line_not_success_id.m2_total_line_discount)
            if round(total_amount_line) != r.amount_total:
                order_error.append(r.name)
        if len(order_error) > 0:
            raise ValidationError(order_error)
        else:
            raise ValidationError('OK')