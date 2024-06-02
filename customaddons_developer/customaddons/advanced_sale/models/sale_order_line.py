from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    m2_is_global_discount = fields.Boolean(default=False)
    m2_total_line_discount = fields.Float(default=0.0)

    boo_total_discount = fields.Float(compute='_compute_boo_total_discount', store=True)
    boo_total_discount_percentage = fields.Float(compute='_compute_boo_total_discount', store=True)
    boo_phan_bo_price_total = fields.Float(compute='_compute_boo_total_discount', string="Phân bổ thành tiền",
                                           store=True)
    thuong_hieu = fields.Many2one('s.product.brand', string="Thương hiệu", related='product_id.thuong_hieu')
    is_product_green = fields.Boolean(related='product_id.is_product_green')
    categ_id = fields.Many2one('product.category', related='product_id.categ_id')
    shipping_code = fields.Char(string="Mã vận đơn", compute="_compute_shipping_code")
    refunded_orderline_id = fields.Many2one('sale.order.line', 'Refunded Order Line')
    s_store_code = fields.Char(string='Mã kho dành cho DWH')
    s_lst_price = fields.Float(string='Giá bán', compute='_compute_s_lst_price', store=True)
    quantity_program_duplicate = fields.Float(string='Số lượng CTKM duplicate trong đơn hàng đã tách line',
                                              compute='_compute_quantity_coupon_program_duplicate_line_split',
                                              store=True)
    is_line_coupon_program = fields.Boolean(string='Là line CTKM', default=False)
    program_name = fields.Char(string='Tên CTKM', related='coupon_program_id.name', store=True)
    is_ecommerce_reward_line = fields.Boolean(string='Là line trừ tiền của đơn hàng ecommerce', default=False)
    is_product_reward = fields.Char(string='Là Line trừ tiền', default=False)

    @api.depends('order_id')
    def _compute_quantity_coupon_program_duplicate_line_split(self):
        for r in self:
            r.quantity_program_duplicate = 1
            if r.coupon_program_id:
                for order_line_id in r.order_id.order_line:
                    if r.id != order_line_id.id and r.coupon_program_id.id == order_line_id.coupon_program_id.id:
                        r.quantity_program_duplicate += 1

    @api.depends('order_id')
    def _compute_quantity_coupon_program_duplicate_line_split(self):
        for r in self:
            r.quantity_program_duplicate = 1
            if r.coupon_program_id:
                for order_line_id in r.order_id.order_line:
                    if r.id != order_line_id.id and r.coupon_program_id.id == order_line_id.coupon_program_id.id:
                        r.quantity_program_duplicate += 1

    @api.depends('product_id')
    def _compute_s_lst_price(self):
        for rec in self:
            if rec.product_id:
                if not rec.is_product_reward:
                    rec.s_lst_price = rec.product_id.lst_price
                else:
                    rec.s_lst_price = -rec.product_id.lst_price

    def _compute_shipping_code(self):
        for rec in self:
            shipping_code = ''
            stock_move = rec.env['stock.move'].search([('sale_line_id', '=', rec.id)])
            if stock_move:
                shipping_label_list = []
                for move in stock_move:
                    if move.picking_id and move.picking_id.shipping_label:
                        if move.picking_id.shipping_label not in shipping_label_list:
                            shipping_label_list.append(move.picking_id.shipping_label)
                if len(shipping_label_list) > 0:
                    shipping_code = ', '.join(shipping_label_list)
            rec.sudo().shipping_code = shipping_code

    # @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'm2_total_line_discount',
    #              'm2_is_global_discount')
    # def _compute_amount(self):
    #     for line in self:
    #         price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
    #         taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
    #                                         product=line.product_id, partner=line.order_id.partner_shipping_id)
    #         line.update({
    #             'price_tax': taxes['total_included'] - taxes['total_excluded'],
    #             'price_total': taxes['total_included'] - line.m2_total_line_discount,
    #             'price_subtotal': taxes['total_excluded'] - line.m2_total_line_discount,
    #         })
    #         if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
    #                 'account.group_account_manager'):
    #             line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    def is_free_product(self):
        for rec in self:
            if rec.coupon_program_id:
                if rec.coupon_program_id.reward_type == "product":
                    return True
                else:
                    return False

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'm2_total_line_discount',
                 'm2_is_global_discount')
    def _compute_boo_total_discount(self):
        total_discount = 0
        refund_total_discount = 0
        total_global_discount = 0
        refund_total_global_discount = 0
        total_qty = 0
        for e in self[0].order_id.order_line:
            # SO line discount
            if e.m2_is_global_discount:
                if e.refunded_orderline_id:
                    refund_total_global_discount += e.price_total
                    refund_total_discount += e.price_total
                else:
                    total_global_discount += e.price_total
                    total_discount += e.price_total
            elif e.is_ecommerce_reward_line:
                if e.refunded_orderline_id:
                    refund_total_discount += e.price_total
                else:
                    total_discount += e.price_total
                # total_discount += e.price_total
            elif e.coupon_program_id or e.gift_card_id or e.is_line_coupon_program:
                free_product = e.is_free_product()
                if free_product or not self[0].order_id.is_magento_order or not self[0].order_id.is_invisible_ecommerce:
                    if e.refunded_orderline_id:
                        refund_total_discount += e.price_total
                    else:
                        total_discount += e.price_total
            # SO line
            # else:
            #     total_qty += e.product_uom_qty
            # total_discount += -e.m2_total_line_discount
        if total_qty == 0:
            total_qty = 1
        total_global_discount = -total_global_discount
        # tong discount SO tinh ca discount tung line va discount ca SO
        total_discount = -total_discount
        for line in self[0].order_id.order_line:
            boo_total_discount = 0
            boo_total_discount_percentage = 0
            price_total_so = 0
            refund_price_total_so = 0
            line.update({
                'boo_phan_bo_price_total': 0,
                'boo_total_discount': 0,
                'boo_total_discount_percentage': 0,
            })
            if line.refunded_orderline_id:
                refund_price_total_so = sum(
                    [line.price_unit * line.product_uom_qty for line in self[0].order_id.order_line if
                     not line.m2_is_global_discount and not line.coupon_program_id and not line.is_delivery and not line.gift_card_id
                     and not line.is_ecommerce_reward_line and not line.is_line_coupon_program and line.refunded_orderline_id])
            else:
                price_total_so = sum([line.price_unit * line.product_uom_qty for line in self[0].order_id.order_line if
                                      not line.m2_is_global_discount and not line.coupon_program_id and not line.is_delivery and not line.gift_card_id
                                      and not line.is_ecommerce_reward_line and not line.is_line_coupon_program and not line.refunded_orderline_id])
            # if total_discount > 0:
            if self[0].order_id.is_magento_order:
                # boo_total_discount = (line.product_id.lst_price - line.price_unit)*line.product_uom_qty + line.m2_total_line_discount
                if not line.is_product_reward:
                    boo_total_discount = (line.s_lst_price - line.price_unit) * line.product_uom_qty
                else:
                    boo_total_discount = (-line.s_lst_price - line.price_unit) * line.product_uom_qty
            else:
                # sp mien phi
                if line.is_free_product() or line.price_unit == 0:
                    if 0 <= line.price_unit < line.s_lst_price:
                        boo_total_discount = (line.s_lst_price - line.price_unit) * line.product_uom_qty + line.price_unit
                else:
                    if 0 <= line.price_unit < line.s_lst_price or line.discount:
                        boo_total_discount = (line.s_lst_price - line.price_unit) * line.product_uom_qty + (
                                line.product_uom_qty * line.price_unit) * line.discount / 100
            # boo_total_discount = total_global_discount / total_qty * line.product_uom_qty + line.m2_total_line_discount
            # boo_total_discount_percentage = boo_total_discount / total_discount * 100
            if line.refunded_orderline_id:
                if refund_price_total_so != 0 and not line.is_free_product() and not line.is_delivery and not line.is_line_coupon_program:
                    boo_total_discount_percentage = refund_total_discount * (
                        ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) *
                         line.discount / 100) / refund_price_total_so)
            else:
                if price_total_so != 0:
                    if not line.is_free_product() and not line.is_delivery and not line.is_line_coupon_program and not line.coupon_program_id and not line.gift_card_id:
                        if self[0].order_id.is_magento_order:
                            boo_total_discount_percentage = total_discount * (((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) * line.discount / 100) / price_total_so)
                        else:
                            boo_total_discount_percentage = total_discount * (
                                    ((line.price_unit * line.product_uom_qty) - (
                                                line.price_unit * line.product_uom_qty) *
                                     line.discount / 100) / price_total_so)

            if not line.m2_is_global_discount:
                line.update({
                    'boo_phan_bo_price_total': line.price_total,
                    'boo_total_discount': abs(boo_total_discount),
                    'boo_total_discount_percentage': abs(boo_total_discount_percentage) if not line.is_product_reward
                    else boo_total_discount_percentage,
                })
                if line.product_uom_qty < 0:
                    line.update({
                        'boo_phan_bo_price_total': line.price_total,
                        'boo_total_discount': -boo_total_discount,
                        'boo_total_discount_percentage': -boo_total_discount_percentage,
                    })
                # line.update({
                #     'boo_phan_bo_price_total': line.price_total,
                #     'boo_total_discount': line.m2_total_line_discount + boo_total_discount,
                #     'boo_total_discount_percentage': boo_total_discount_percentage,
                # })

    def action_compute_boo_total_discount(self):
        total_discount = 0
        refund_total_discount = 0
        total_global_discount = 0
        refund_total_global_discount = 0
        total_qty = 0
        for e in self[0].order_id.order_line:
            # SO line discount
            if e.m2_is_global_discount:
                if e.refunded_orderline_id:
                    refund_total_global_discount += e.price_total
                    refund_total_discount += e.price_total
                else:
                    total_global_discount += e.price_total
                    total_discount += e.price_total
            elif e.is_ecommerce_reward_line:
                if e.refunded_orderline_id:
                    refund_total_discount += e.price_total
                else:
                    total_discount += e.price_total
                # total_discount += e.price_total
            elif e.coupon_program_id or e.gift_card_id or e.is_line_coupon_program:
                free_product = e.is_free_product()
                if free_product or not self[0].order_id.is_magento_order or not self[0].order_id.is_invisible_ecommerce:
                    if e.refunded_orderline_id:
                        refund_total_discount += e.price_total
                    else:
                        total_discount += e.price_total
        if total_qty == 0:
            total_qty = 1
        total_global_discount = -total_global_discount
        # tong discount SO tinh ca discount tung line va discount ca SO
        total_discount = -total_discount
        for line in self[0].order_id.order_line:
            boo_total_discount = 0
            boo_total_discount_percentage = 0
            price_total_so = 0
            refund_price_total_so = 0
            self._cr.execute("""UPDATE sale_order_line SET boo_phan_bo_price_total = 0 WHERE id = %s""",
                             (line.id,))
            self._cr.execute("""UPDATE sale_order_line SET boo_total_discount = 0 WHERE id = %s""",
                             (line.id,))
            self._cr.execute("""UPDATE sale_order_line SET boo_total_discount_percentage = 0 WHERE id = %s""",
                             (line.id,))
            if line.refunded_orderline_id:
                refund_price_total_so = sum(
                    [line.price_unit * line.product_uom_qty for line in self[0].order_id.order_line if
                     not line.m2_is_global_discount and not line.coupon_program_id and not line.is_delivery and not line.gift_card_id
                     and not line.is_ecommerce_reward_line and not line.is_line_coupon_program and line.refunded_orderline_id])
            else:
                price_total_so = sum([line.price_unit * line.product_uom_qty for line in self[0].order_id.order_line if
                                      not line.m2_is_global_discount and not line.coupon_program_id and not line.is_delivery and not line.gift_card_id
                                      and not line.is_ecommerce_reward_line and not line.is_line_coupon_program and not line.refunded_orderline_id])
            if self[0].order_id.is_magento_order:
                if not line.is_product_reward:
                    boo_total_discount = (line.s_lst_price - line.price_unit) * line.product_uom_qty
                else:
                    boo_total_discount = (-line.s_lst_price - line.price_unit) * line.product_uom_qty
            else:
                # sp mien phi
                if line.is_free_product() or line.price_unit == 0:
                    if 0 <= line.price_unit < line.s_lst_price:
                        boo_total_discount = (
                                                         line.s_lst_price - line.price_unit) * line.product_uom_qty + line.price_unit
                else:
                    if 0 <= line.price_unit < line.s_lst_price or line.discount:
                        boo_total_discount = (line.s_lst_price - line.price_unit) * line.product_uom_qty + (
                                line.product_uom_qty * line.price_unit) * line.discount / 100
            if line.refunded_orderline_id:
                if refund_price_total_so != 0 and not line.is_free_product() and not line.is_delivery and not line.is_line_coupon_program:
                    boo_total_discount_percentage = refund_price_total_so * (
                            ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) *
                             line.discount / 100) / refund_price_total_so)
            else:
                if price_total_so != 0:
                    if not line.is_free_product() and not line.is_delivery and not line.is_line_coupon_program and not line.coupon_program_id and not line.gift_card_id:
                        if self[0].order_id.is_magento_order:
                            boo_total_discount_percentage = total_discount * (((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) * line.discount / 100) / price_total_so)
                        else:
                            boo_total_discount_percentage = total_discount * (
                                    ((line.price_unit * line.product_uom_qty) - (
                                            line.price_unit * line.product_uom_qty) *
                                     line.discount / 100) / price_total_so)

            if not line.m2_is_global_discount:
                boo_total_discount_percentage_value = boo_total_discount_percentage
                if not line.is_product_reward:
                    boo_total_discount_percentage_value = abs(boo_total_discount_percentage)
                self._cr.execute("""UPDATE sale_order_line SET boo_phan_bo_price_total = %s WHERE id = %s""",
                                 (line.price_total, line.id))
                self._cr.execute("""UPDATE sale_order_line SET boo_total_discount = %s WHERE id = %s""",
                                 (abs(boo_total_discount), line.id))
                self._cr.execute("""UPDATE sale_order_line SET boo_total_discount_percentage = %s WHERE id = %s""",
                                 (boo_total_discount_percentage_value, line.id))
                if line.product_uom_qty < 0:
                    self._cr.execute("""UPDATE sale_order_line SET boo_phan_bo_price_total = %s WHERE id = %s""",
                                     (line.price_total, line.id))
                    self._cr.execute("""UPDATE sale_order_line SET boo_total_discount = %s WHERE id = %s""",
                                     (-boo_total_discount, line.id))
                    self._cr.execute("""UPDATE sale_order_line SET boo_total_discount_percentage = %s WHERE id = %s""",
                                     (-boo_total_discount_percentage, line.id))
