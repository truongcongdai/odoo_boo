from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_return_order = fields.Boolean(string='Là đơn đổi trả', default=False)
    is_magento_order = fields.Boolean(string='Đơn hàng từ Magento', default=False)
    return_order_id = fields.Many2one('sale.order', string='Đơn đổi trả')
    return_order_ids = fields.One2many('sale.order', 'return_order_id')
    count_return_order = fields.Integer('Đơn trả hàng', compute="compute_count_return_order")
    applied_program_ids = fields.Many2many(
        "coupon.program", 'rel_so_applied_program',
        string="Applied Programs")
    loyalty_points = fields.Float()
    is_sell_wholesale = fields.Boolean('Đơn bán buôn')
    # warehouse_name = fields.Char(string='Kho hàng', compute='_compute_warehouse_name')
    pos_name = fields.Char(string='Điểm bán hàng', compute='_compute_stock_picking_ids')
    is_done_delivery = fields.Boolean(string="Đã giao đủ hàng", compute="compute_is_done_delivery", store=True)

    color_list = fields.Char(string='Danh sách màu', compute='_compute_color_brand_size_category', store=True)
    brand_list = fields.Char(string='Danh sách thương hiệu', compute='_compute_color_brand_size_category', store=True)
    size_list = fields.Char(string='Danh sách kích thước', compute='_compute_color_brand_size_category', store=True)
    category_list = fields.Char(string='Danh sách nhóm sản phẩm', compute='_compute_color_brand_size_category',
                                store=True)
    chuong_trinh_khuyen_mai = fields.Char(string="Chương trình khuyến mãi",
                                          related='applied_program_ids.name', store=True)
    # customer_ranked = fields.Char(string="Hạng", related='partner_id.customer_ranked', store=True)
    customer_ranked = fields.Char(string="Hạng", compute='_compute_partner_customer_ranked', store=True)
    s_store_code = fields.Char(string='Mã kho dành cho DWH', compute='_compute_sale_order_picking_warehouse_id',
                               store=True)
    date_order_sale_filter = fields.Datetime(string="Date filter", compute="_compute_date_order_sale_filter", store=True)
    is_ecommerce_order = fields.Boolean(string='Là đơn hàng ecommerce',compute='_compute_is_ecommerce_order', default=False,store=True)
    coupon_code = fields.Char('Coupon Code')
    s_promo_code = fields.Char('Promo Code')
    pos_order_id_dashboard = fields.Many2one('pos.order', string='Pos Order', readonly=True)
    is_invisible_ecommerce = fields.Boolean()
    s_promo_program_m2 = fields.Char(compute='_compute_program_so_m2', string='Chương trình khuyến mãi', store=True)
    s_shipping_label = fields.Char(string='Mã vận đơn', compute='_compute_s_shipping_label')
    s_is_admin = fields.Boolean(string='Is Admin', compute='_compute_s_is_admin')

    def _compute_s_is_admin(self):
        for r in self:
            r.s_is_admin = self.env.user.has_group('advanced_sale.s_boo_group_administration') or self.env.user.has_group('base.group_system')

    @api.depends('partner_id.customer_ranked')
    def _compute_partner_customer_ranked(self):
        for r in self:
            if r.ids:
                customer_ranked_old = r.customer_ranked
                self._cr.execute(
                    """UPDATE sale_order SET customer_ranked = %s WHERE id = %s""",
                    (False, r.ids[0]))
                if customer_ranked_old:
                    self._cr.execute(
                        """UPDATE sale_order SET customer_ranked = %s WHERE id = %s""",
                        (customer_ranked_old, r.ids[0]))
                if r.partner_id.customer_ranked and r.partner_id.customer_ranked != customer_ranked_old:
                    self._cr.execute(
                        """UPDATE sale_order SET customer_ranked = %s WHERE id = %s""",
                        (r.partner_id.customer_ranked, r.ids[0]))
            else:
                r.customer_ranked = False

    @api.depends('s_promo_code', 'coupon_code')
    def _compute_program_so_m2(self):
        for rec in self:
            rec.s_promo_program_m2 = False
            s_promo_program_ids = []
            if rec.s_promo_code:
                list_promo_code = rec.s_promo_code.split(',')
                for e in list_promo_code:
                    self._cr.execute(
                        """SELECT * FROM coupon_program WHERE ma_ctkm = %s LIMIT 1""",
                        (e,))
                    promo_code = self._cr.dictfetchall()
                    if len(promo_code) > 0:
                        if len(s_promo_program_ids):
                            rec.s_promo_program_m2 += ',' + promo_code[0].get('name')
                        elif promo_code[0].get('id') not in s_promo_program_ids:
                            rec.s_promo_program_m2 = promo_code[0].get('name')
                        s_promo_program_ids.append(promo_code[0].get('id'))
            if rec.coupon_code:
                list_coupon_code = rec.coupon_code.split(',')
                for e in list_coupon_code:
                    self._cr.execute(
                        """SELECT * FROM coupon_coupon WHERE boo_code = %s LIMIT 1""",
                        (e,))
                    coupon_code = self._cr.dictfetchall()
                    if len(coupon_code) > 0:
                        self._cr.execute(
                            """SELECT * FROM coupon_program WHERE id = %s LIMIT 1""",
                            (coupon_code[0].get('program_id'),))
                        coupon_program_id = self._cr.dictfetchall()
                        if len(coupon_program_id) > 0 and coupon_program_id[0].get('id') not in s_promo_program_ids:
                            if len(s_promo_program_ids):
                                rec.s_promo_program_m2 += ',' + coupon_program_id[0].get('name')
                            else:
                                rec.s_promo_program_m2 = coupon_program_id[0].get('name')
                            s_promo_program_ids.append(coupon_program_id[0].get('id'))

    def _compute_s_shipping_label(self):
        for rec in self:
            rec.s_shipping_label = False
            label = ''
            if len(rec.picking_ids) > 0:
                for picking in rec.picking_ids:
                    if picking.shipping_label:
                        if label:
                            label += ', ' + picking.shipping_label
                        else:
                            label += picking.shipping_label
                if len(label) > 0:
                    rec.sudo().s_shipping_label = label

    def _cron_compute_is_invisible_ecommerce(self):
        sale_order_ids = self.env['sale.order'].sudo().search(['|', '|', '|', ('is_magento_order', '=', True),
                                                               ('is_lazada_order', '=', True),
                                                               ('is_tiktok_order', '=', True),
                                                               ('s_shopee_is_order', '=', True),
                                                               ('is_invisible_ecommerce', '=', False)])
        for rec in sale_order_ids:
            if not rec.is_invisible_ecommerce:
                self._cr.execute(
                    """UPDATE sale_order SET is_invisible_ecommerce = %s WHERE id = %s""",
                    (True, rec.id))

    @api.depends('date_order')
    def _compute_date_order_sale_filter(self):
        for rec in self:
            if rec.date_order:
                rec.date_order_sale_filter = rec.date_order + timedelta(hours=7)

    @api.depends('is_magento_order')
    def _compute_is_ecommerce_order(self):
        for rec in self:
            rec.sudo().is_ecommerce_order = False
            if rec.is_magento_order == True:
                rec.sudo().write({
                    'is_ecommerce_order': True
                })

    @api.depends('picking_ids')
    def _compute_sale_order_picking_warehouse_id(self):
        for rec in self:
            rec.s_store_code = ''
            picking_ids = rec.picking_ids.filtered(lambda p: p.state in ['assigned', 'done'])
            if picking_ids:
                for picking in picking_ids:
                    if picking.location_id:
                        if picking.location_id.warehouse_id:
                            if picking.location_id.warehouse_id.pos_config_ids:
                                so_pos_config_ids = picking.location_id.warehouse_id.pos_config_ids
                                if not so_pos_config_ids:
                                    rec.s_store_code += str(picking.location_id.warehouse_id.code) + ','
                                for so_pos_config_id in so_pos_config_ids:
                                    rec.s_store_code += str(so_pos_config_id.code) + ','
            rec.s_store_code = rec.s_store_code.rstrip(', ')
            order_line_ids = rec.order_line.filtered(lambda l: l.product_id.type == 'product')
            if order_line_ids:
                for line in order_line_ids:
                    line.s_store_code = ''
                    for stock_move in line.move_ids:
                        if stock_move.picking_id:
                            if stock_move.picking_id.s_warehouse_id:
                                if stock_move.picking_id.s_warehouse_id.pos_config_ids:
                                    line_pos_config_ids = stock_move.picking_id.s_warehouse_id.pos_config_ids
                                    if not line_pos_config_ids:
                                        line.s_store_code += stock_move.picking_id.s_warehouse_id.code + ', '
                                    for line_pos_config_id in line_pos_config_ids:
                                        line.s_store_code += line_pos_config_id.code + ', '
                    line.s_store_code = line.s_store_code.rstrip(', ')

    def _get_action_view_picking(self, pickings):
        action = super(SaleOrder, self)._get_action_view_picking(pickings)
        if 'context' in action:
            action['context']['edit'] = True
        else:
            action['context'] = {'edit': True}
        return action

    @api.depends('order_line')
    def _compute_color_brand_size_category(self):
        for rec in self:
            rec.color_list = ''
            rec.brand_list = ''
            rec.size_list = ''
            rec.category_list = ''
            color, brand, size, category = '', '', '', ''
            if rec.order_line:
                for line in rec.order_line:
                    if line.product_id.mau_sac:
                        color_line = line.product_id.mau_sac
                        if color_line not in color:
                            color += color_line + ', '
                    if line.product_id.thuong_hieu.name:
                        brand_line = line.product_id.thuong_hieu.name
                        if brand_line not in brand:
                            brand += brand_line + ', '
                    if line.product_id.kich_thuoc:
                        size_line = line.product_id.kich_thuoc
                        if size_line not in size:
                            size += size_line + ', '
                    if line.product_id.categ_id:
                        category_line = line.product_id.categ_id.name
                        if category_line not in category:
                            category += category_line + ', '
                rec.color_list = color.rstrip(', ')
                rec.brand_list = brand.rstrip(', ')
                rec.size_list = size.rstrip(', ')
                rec.category_list = category.rstrip(', ')

    @api.depends('order_line', 'order_line.qty_delivered', 'order_line.product_uom_qty')
    def compute_is_done_delivery(self):
        for rec in self:
            is_done_delivery = True
            if rec.order_line:
                for line in rec.order_line:
                    if line.qty_delivered < line.product_uom_qty and line.product_id.detailed_type == 'product':
                        is_done_delivery = False
                        break
            rec.sudo().is_done_delivery = is_done_delivery

    def _compute_stock_picking_ids(self):
        for rec in self:
            rec.pos_name = ''
            location_name = ''
            if rec.picking_ids:
                if rec.picking_ids.mapped('location_id'):
                    for location in rec.picking_ids.mapped('location_id'):
                        location_name += location.s_complete_name + ','
            rec.pos_name = location_name.rstrip(',')

    # def _compute_warehouse_name(self):
    #     for r in self:
    #         r.warehouse_name = None
    #         location_name = ''
    #         if r.picking_ids:
    #             if r.picking_ids.mapped('location_id'):
    #                 for location in r.picking_ids.mapped('location_id'):
    #                     location_name += location.s_complete_name + ','
    #         r.warehouse_name = location_name.rstrip(',')

    def compute_count_return_order(self):
        for rec in self:
            rec.count_return_order = 0
            if len(rec.return_order_ids) > 0:
                rec.count_return_order = len(rec.return_order_ids)

    @api.depends('order_line.price_total', 'is_return_order')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            if not order.is_return_order:
                amount_untaxed = amount_tax = 0.0
                for line in order.order_line:
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
                order.update({
                    'amount_untaxed': amount_untaxed,
                    'amount_tax': amount_tax,
                    'amount_total': amount_untaxed + amount_tax,
                })
            else:
                amount_untaxed = amount_tax = 0.0
                for line in order.order_line:
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
                amount_total = amount_untaxed + amount_tax
                if amount_total > 0:
                    order.update({
                        'amount_untaxed': amount_untaxed,
                        'amount_tax': amount_tax,
                        'amount_total': amount_untaxed + amount_tax,
                    })
                else:
                    order.update({
                        'amount_untaxed': 0,
                        'amount_tax': 0,
                        'amount_total': 0,
                    })

    def _mass_action_compute_source_id(self):
        orders_return = self.env['sale.order'].sudo().search(['|', ('return_order_id', '!=', False), ('is_return_order', '=', True), ('source_id', '=', False)])
        for order_return in orders_return:
            order_return.source_id = order_return.return_order_id.source_id.id

    def create_return_sale_order(self):
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
                # source = self.env.ref('advanced_sale.utm_source_magento_order').id
                # if rec.is_magento_order and rec.source_id.id == source:
                #     sale_order.update({
                #         'source_id': source
                #     })

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

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đơn trả hàng',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.return_order_ids.ids)],
            'context': {'create': False, 'edit': True},
        }

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SaleOrder, self).create(vals_list)
        if res.partner_id:
            res.partner_id.sudo()._edit_last_order()
            if res.state in ('sale', 'done'):
                count_partner_order = len(res.partner_id.sale_order_ids) + len(res.partner_id.pos_order_ids)
                if count_partner_order == 1:
                    res.sudo().partner_id.write({
                        'is_new_customer': True,
                    })
                else:
                    res.sudo().partner_id.write({
                        'is_new_customer': False,
                    })
        sale_source_id = self.env.ref('advanced_sale.utm_source_sale')
        ban_buon_source_id = self.env.ref('advanced_sale.utm_source_sell_wholesale')
        if not res.return_order_id:
            if res.is_sell_wholesale:
                source_id = ban_buon_source_id.id
                res.sudo().write({
                    'source_id': source_id
                })
            elif (not res.is_tiktok_order and not res.is_lazada_order and not res.s_shopee_is_order and
                  not res.is_sell_wholesale and not res.is_magento_order):
                source_id = sale_source_id.id
                res.sudo().write({
                    'source_id': source_id
                })
        elif res.return_order_id and res.return_order_id.source_id:
            source_id = res.return_order_id.source_id.id
            res.sudo().write({
                'source_id': source_id
            })
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if vals.get('state') and self.partner_id:
            if self.state in ('sale', 'done'):
                count_partner_order = len(self.partner_id.sale_order_ids) + len(self.partner_id.pos_order_ids)
                if count_partner_order == 1:
                    self.sudo().partner_id.write({
                        'is_new_customer': True,
                    })
                else:
                    self.sudo().partner_id.write({
                        'is_new_customer': False,
                    })
        return res

    def _get_reward_values_product(self, program):
        reward_product = self.order_line.filtered(lambda line: program.reward_product_id == line.product_id)
        if not reward_product:
            raise ValidationError('Bạn cần phải thêm sản phẩm %s có SKU "%s" vào đơn hàng' % (
                program.reward_product_id.name, program.reward_product_id.default_code))
        res = super(SaleOrder, self)._get_reward_values_product(program)
        return res

    def _action_cancel(self):
        for rec in self:
            if rec.partner_id:
                invoices = self.env['account.move'].sudo().search([('id', 'in', rec.invoice_ids.ids)])
                if invoices:
                    for invoice in invoices:
                        rec.partner_id.write({
                            'loyalty_points': rec.partner_id.loyalty_points - invoice.loyalty_points
                        })
        return super(SaleOrder, self)._action_cancel()

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Đơn Bán Buôn',
            'template': '/advanced_sale/static/xlsx/template_import_don_ban_buon.xlsx'
        }]


class SaleCouponApplyCode(models.TransientModel):
    _inherit = 'sale.coupon.apply.code'

    def apply_coupon(self, order, coupon_code):
        error_status = {}
        coupon = self.env['coupon.coupon'].search([('boo_code', '=', coupon_code)], limit=1)
        if coupon:
            error_status = coupon._check_coupon_code(order.date_order.date(), order.partner_id.id, order=order)
            if not error_status:
                # Consume coupon only if reward lines were created
                order_line_count = len(order.order_line)
                if coupon.program_id.discount_type == 'percentage':
                    coupon_program_ids = order.order_line.mapped('coupon_program_id')

                    if not coupon_program_ids or coupon.program_id.discount_apply_on not in coupon_program_ids.mapped('discount_apply_on'):
                        order._create_reward_line(coupon.program_id)
                        if order_line_count < len(order.order_line):
                            order.applied_coupon_ids += coupon
                            coupon.write({'state': 'used'})

                    elif coupon.program_id.discount_apply_on in coupon_program_ids.mapped('discount_apply_on'):
                        if coupon.program_id.discount_apply_on == 'on_order':
                            line_id = order.order_line.filtered(lambda l: l.coupon_program_id.discount_apply_on == 'on_order')
                            if line_id and coupon.program_id.discount_percentage > line_id.coupon_program_id.discount_percentage:
                                line_id.unlink()
                                order._create_reward_line(coupon.program_id)
                                order.applied_coupon_ids += coupon
                                coupon.write({'state': 'used'})

                elif coupon.program_id.discount_type == 'fixed_amount':
                    order._create_reward_line(coupon.program_id)
                    if order_line_count < len(order.order_line):
                        order.applied_coupon_ids += coupon
                        coupon.write({'state': 'used'})

            return error_status
        return super(SaleCouponApplyCode, self).apply_coupon(order, coupon_code)
