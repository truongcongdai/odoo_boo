from odoo import fields, models, api


class SPosOrderLineInherit(models.Model):
    _inherit = 'pos.order.line'

    boo_total_discount = fields.Float(compute='_compute_boo_total_discount', store=True)
    boo_total_discount_percentage = fields.Float(compute='_compute_boo_total_discount', store=True)
    is_free_product = fields.Boolean(string="Là sản phẩm miễn phí", compute="_compute_free_product", store=True)
    boo_phan_bo_price_total = fields.Float(compute='_compute_boo_total_discount', string="Phân bổ thành tiền",
                                           store=True)
    s_lst_price = fields.Float(string='Giá bán', compute='_compute_s_lst_price', store=True)
    s_product_barcode = fields.Char(related='product_id.barcode')
    s_store_code = fields.Char(string='Mã kho dành cho DWH')
    s_pos_reference = fields.Char(string='Mã biên lai', related='order_id.pos_reference')
    s_gift_card_code = fields.Char(string='Gift card code', store=True)
    program_name = fields.Char(string='Tên CTKM', related='program_id.name', store=True)
    is_line_gift_card = fields.Boolean(string='Là line giftcard', compute='_compute_gift_card_id', store=True)
    is_product_service = fields.Boolean(string='Sản phẩm dịch vụ', compute='_compute_is_product_service', store=True)
    quantity_program_duplicate = fields.Float(string='Số lượng CTKM duplicate trong đơn hàng',
                                                compute='_compute_quantity_program_duplicate', store=True)
    cheapest_line_id = fields.Integer(string='ID line có SP rẻ nhất')
    is_line_cheapest_refund = fields.Boolean(string='Là line refund áp dụng CTKM SP rẻ nhất')
    s_chanel_discount = fields.Float(string='Chanel Discount')
    s_crm_discount = fields.Float(string='CRM Discount')
    s_hr_discount = fields.Float(string='HR Discount')
    s_type_discount = fields.Selection([
        ('chanel', 'Channel'),
        ('crm', 'CRM'),
        ('hr', 'HR')
    ], string='Loại Discount', compute='_compute_type_discount_pos', store=True)

    @api.depends('s_chanel_discount', 's_crm_discount', 's_hr_discount')
    def _compute_type_discount_pos(self):
        for rec in self:
            rec.s_type_discount = False
            if rec.program_id and rec.program_id.reward_type == 'discount' and rec.program_id.s_type_discount and rec.product_id.detailed_type == 'service':
                if rec.program_id.s_type_discount == 'chanel':
                    rec.s_type_discount = 'chanel'
                elif rec.program_id.s_type_discount == 'crm':
                    rec.s_type_discount = 'crm'
                elif rec.program_id.s_type_discount == 'hr':
                    rec.s_type_discount = 'hr'
            elif rec.gift_card_id and rec.gift_card_id.s_type_discount and not rec.gift_card_id.is_not_calculate_amount:
                if rec.gift_card_id.s_type_discount == 'chanel':
                    rec.s_type_discount = 'chanel'
                elif rec.gift_card_id.s_type_discount == 'crm':
                    rec.s_type_discount = 'crm'
                elif rec.gift_card_id.s_type_discount == 'hr':
                    rec.s_type_discount = 'hr'

    @api.depends('product_id')
    def _compute_quantity_program_duplicate(self):
        for r in self:
            r.quantity_program_duplicate = 1
            if r.program_id:
                for order_line_id in r.order_id.lines:
                    if r.id != order_line_id.id and r.program_id.id == order_line_id.program_id.id:
                        r.quantity_program_duplicate += 1

    def _cron_compute_quantity_program_duplicate(self):
        line_program_ids = self.search([])
        for r in line_program_ids:
            self._cr.execute("""UPDATE pos_order_line SET quantity_program_duplicate = 1 WHERE id = %s""" % (r.id,))
            if r.program_id:
                for order_line_id in r.order_id.lines:
                    if r.id != order_line_id.id and r.program_id.id == order_line_id.program_id.id:
                        self._cr.execute(
                            """UPDATE pos_order_line SET quantity_program_duplicate = quantity_program_duplicate + 1 WHERE id = %s""" % (r.id,))

    @api.depends('product_id')
    def _compute_is_product_service(self):
        for r in self:
            r.is_product_service = False
            if r.product_id.detailed_type == 'service' and not r.program_id and not r.coupon_id and not r.is_line_gift_card:
                r.is_product_service = True

    @api.depends('gift_card_id')
    def _compute_gift_card_id(self):
        for r in self:
            r.is_line_gift_card = False
            if (r.s_gift_card_code or r.gift_card_id) and (r.product_id.detailed_type == 'service' and not r.program_id and not r.coupon_id):
                r.is_line_gift_card = True

    def cron_compute_gift_card_id(self):
        line_gift_card_ids = self.search([]).filtered(lambda l: (l.s_gift_card_code or l.gift_card_id) and l.product_id.detailed_type == 'service' and not l.program_id and not l.coupon_id)
        if line_gift_card_ids:
            for line_gift_card_id in line_gift_card_ids:
                if not line_gift_card_id.is_line_gift_card:
                    self._cr.execute(
                        """UPDATE pos_order_line SET is_line_gift_card = True WHERE id = %s""",
                        (line_gift_card_id.id,))

    @api.depends('product_id')
    def _compute_s_lst_price(self):
        for rec in self:
            if rec.product_id:
                rec.s_lst_price = rec.product_id.lst_price

    # def is_global_discount(self):
    #     if self.gift_card_id and self.id in self.gift_card_id.redeem_pos_order_line_ids.ids:
    #         return True
    #     elif self.program_id and self.id in self.program_id.pos_order_line_ids.ids and self.program_id.discount_type == "fixed_amount":
    #         return True
    #     elif self.program_id and self.id in self.program_id.pos_order_line_ids.ids and self.program_id.discount_apply_on == "on_order":
    #         return True
    #     else:
    #         return False

    # def is_discount_on_specific_product(self,rec):
    #     if rec.program_id and rec.id in rec.program_id.pos_order_line_ids.ids and rec.program_id.discount_apply_on == 'specific_products':
    #         return True
    #     else:
    #         return False

    # def is_discount_on_cheapest_product(self,rec):
    #     if rec.program_id and rec.id in rec.program_id.pos_order_line_ids.ids and rec.program_id.discount_apply_on == 'cheapest_product':
    #         return True
    #     else:
    #         return False

    # Lấy ra các line sp được giảm giá
    # def mapping_order_line_discount(self):
    #     for rec in self:
    #         if rec.is_discount_on_specific_product(rec):
    #             result = []
    #             for line in rec.order_id.lines:
    #                 if rec.program_id and line.product_id.id in rec.program_id.discount_specific_product_ids.ids:
    #                     result.append(line.id)
    #             return result
    #         if rec.is_discount_on_cheapest_product(rec):
    #             result = -1
    #             order_min = rec.order_id.lines[0].product_id.lst_price/rec.qty
    #             for line in rec.order_id.lines:
    #                 if line.product_id.lst_price/line.qty < order_min and line.product_id.available_in_pos:
    #                     result = line.id
    #             return result

    # Lấy ra số tiền được giảm riêng từng đơn hàng
    # def get_discount_of_line(self):
    #     for rec in self:
    #         amount_discount = 0
    #         for line in rec.order_id.lines:
    #             if line.is_discount_on_specific_product(line):
    #                 if rec.id in line.mapping_order_line_discount():
    #                     amount_discount += rec.price_subtotal_incl * line.program_id.discount_percentage * line.qty / 100
    #             elif line.is_discount_on_cheapest_product(line):
    #                 if rec.id == line.mapping_order_line_discount():
    #                     amount_discount += -line.price_subtotal_incl
    #         return amount_discount
    @api.depends('qty', 'discount', 'price_subtotal_incl', 'order_id.lines')
    def _compute_free_product(self):
        for rec in self:
            is_free_product = False
            for line in rec.order_id.lines:
                if line.refunded_orderline_id:
                    # if not line.refunded_orderline_id.is_reward_product():
                    if rec.refunded_orderline_id.is_free_product:
                        is_free_product = True
                        break
                else:
                    if line.is_reward_product():
                        if rec.product_id.id == line.program_id.reward_product_id.id or rec.product_id.id == int(
                            line.product_id.s_free_product_id) or rec.product_id.id in line.program_id.discount_specific_product_ids.ids:
                            is_free_product = True
                            break
            rec.is_free_product = is_free_product

    def is_reward_product(self):
        for rec in self:
            if rec.program_id:
                # san pham duoc tang
                if rec.program_id.reward_type == "product":
                    return True
                # san pham dac biet va duoc giam 100%
                elif rec.program_id.reward_type == "discount" and rec.program_id.discount_apply_on == "specific_products" and rec.program_id.discount_type == 'percentage' and rec.program_id.discount_percentage == 100:
                    return True
                else:
                    return False
            else:
                return False

    # def is_specific_products(self):
    #     for rec in self:
    #         if rec.program_id and rec.program_id.reward_type == "discount" and rec.program_id.discount_apply_on == "specific_products" and rec.program_id.discount_type == 'percentage' and rec.program_id.discount_percentage == 100:
    #             # san pham duoc tang
    #             return True
    #         # san pham dac biet va duoc giam 100%
    #         # elif rec.program_id.reward_type == "discount" and rec.program_id.discount_apply_on == "specific_products" and rec.program_id.discount_type == 'percentage' and rec.program_id.discount_percentage == 100:
    #         #     return True
    #         else:
    #             return False

    def get_discount_free_product(self):
        for rec in self:
            total_discount = 0
            # if rec.is_free_product:
            for line in rec.order_id.lines:
                if line.is_reward_product():
                    if rec.product_id.id == line.program_id.reward_product_id.id or rec.product_id.id == int(
                            line.product_id.s_free_product_id) or rec.product_id.id in line.program_id.discount_specific_product_ids.ids:
                        # phan biet line refund
                        if rec.product_id.id in line.program_id.discount_specific_product_ids.ids:
                            if rec.qty > 0 and line.qty > 0:
                                total_discount += rec.price_subtotal_incl
                            elif rec.qty < 0 and line.qty < 0:
                                total_discount -= rec.price_subtotal_incl
                        else:
                            if rec.qty > 0 and line.qty > 0:
                                total_discount += -line.price_subtotal_incl
                            elif rec.qty < 0 and line.qty < 0:
                                total_discount += -line.price_subtotal_incl
            return total_discount

    @api.depends('qty', 'discount', 'price_subtotal_incl', 'order_id.lines')
    def _compute_boo_total_discount(self):
        for rec in self:
            total_qty = 0
            # total discount ko tinh sp duoc tang
            total_global_discount = 0
            refund_total_global_discount_positive = 0
            refund_total_global_discount_negative = 0
            # total discount tinh sp duoc tang, san pham dac biet
            total_discount = 0
            refund_total_discount_positive = 0
            refund_total_discount_negative = 0
            price_total_pos = 0
            refund_price_total_pos_positive = 0
            refund_price_total_pos_negative = 0
            for line in rec.order_id.lines:
                # if line.product_id.available_in_pos and not line.is_free_product:
                #     total_qty += 1
                #     price_total_pos += line.price_subtotal_incl
                if not line.product_id.available_in_pos and not line.is_reward_product() and line.product_id.detailed_type == 'service':
                    if line.refunded_orderline_id or (
                            line.sale_order_line_id and line.qty < 0) or line.is_line_cheapest_refund:
                        if line.refunded_orderline_id and line.qty > 0 and rec.order_id.is_cancel_order:
                            refund_total_global_discount_positive += abs(line.price_subtotal_incl)
                            refund_total_discount_positive += abs(line.price_subtotal_incl)
                        else:
                            refund_total_global_discount_negative += line.price_subtotal_incl
                            refund_total_discount_negative += line.price_subtotal_incl
                    else:
                        total_global_discount += line.price_subtotal_incl
                        total_discount += line.price_subtotal_incl
                # ctkm, coupon, giftcard
                elif line.program_id or line.is_line_gift_card or line.is_refund_gift_card() or line.s_is_loyalty_reward_line == True:
                    if not line.is_reward_product():
                        if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                            if line.refunded_orderline_id and line.qty > 0 and rec.order_id.is_cancel_order:
                                refund_total_discount_positive += abs(line.price_subtotal_incl)
                            else:
                                refund_total_discount_negative += line.price_subtotal_incl
                        else:
                            total_discount += line.price_subtotal_incl
                elif line.product_id.available_in_pos and not line.is_free_product:
                    total_qty += 1
                    if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                        if line.refunded_orderline_id and line.qty > 0 and rec.order_id.is_cancel_order:
                            refund_price_total_pos_positive += line.price_subtotal_incl
                        else:
                            refund_price_total_pos_negative += line.price_subtotal_incl
                    else:
                        price_total_pos += line.price_subtotal_incl
            # sp duoc tang voi don hoan tien
            # if rec.order_id.refunded_order_ids:
            #     self._cr.execute(
            #         """SELECT * FROM pos_order_line WHERE program_id is null""",(self.date_from, self.date_to,))
            #     free_product_refund_lines = self.env.cr.dictfetchall()
            #     free_product_refund = rec.order_id.refunded_order_ids.filtered(lambda l: l.program_id)
            if total_qty == 0:
                total_qty = 1
            total_global_discount = -total_global_discount
            total_discount = -total_discount
            order_lines = rec.order_id.lines.sorted(lambda x: x.price_subtotal_incl)
            for line in order_lines:
                boo_total_discount = 0
                boo_total_discount_percentage = 0
                # if total_discount > 0:
                if line.is_free_product:
                    boo_total_discount = line.get_discount_free_product()
                    boo_total_discount_percentage = abs(boo_total_discount)
                    if line.qty < 0:
                        # Chi co line san pham duoc tang - truong hop CTKM tang nhieu san pham
                        free_product_lines = order_lines.filtered(
                            lambda l: not l.is_free_product and l.product_id.detailed_type != 'service' and l.qty < 0)
                        free_product_price_total_pos = sum(order_lines.filtered(
                            lambda
                                l: l.is_free_product and l.product_id.detailed_type != 'service' and l.qty < 0).mapped(
                            'price_subtotal_incl'))
                        total_discount_free_product = sum(order_lines.filtered(
                            lambda
                                l: not l.is_reward_product() and l.product_id.detailed_type == 'service' and l.qty < 0).mapped(
                            'price_subtotal_incl'))
                    else:
                        free_product_lines = order_lines.filtered(
                            lambda l: not l.is_free_product and l.product_id.detailed_type != 'service' and l.qty > 0)
                        free_product_price_total_pos = sum(order_lines.filtered(
                            lambda
                                l: l.is_free_product and l.product_id.detailed_type != 'service' and l.qty > 0).mapped(
                            'price_subtotal_incl'))
                        total_discount_free_product = sum(order_lines.filtered(
                            lambda
                                l: not l.is_reward_product() and l.product_id.detailed_type == 'service' and l.qty > 0).mapped(
                            'price_subtotal_incl'))
                    total_global_discount = 0
                    if 0 <= line.price_unit < line.s_lst_price:
                        total_global_discount = abs((line.s_lst_price - line.price_unit) * line.qty)
                    if len(free_product_lines) == 0:
                        if free_product_price_total_pos != 0:
                            # sp duoc tang hoan tien
                            if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                                boo_total_discount_percentage += abs((total_discount_free_product * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / free_product_price_total_pos)))
                            else:
                                boo_total_discount_percentage += abs(total_discount_free_product * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / free_product_price_total_pos))
                        else:
                            boo_total_discount_percentage = abs(boo_total_discount) + abs(total_discount_free_product)
                    else:
                        if line.qty < 0:
                            boo_total_discount_percentage = boo_total_discount
                    line.update({
                        'boo_phan_bo_price_total': 0,
                        'boo_total_discount': abs(total_global_discount),
                        'boo_total_discount_percentage': abs(boo_total_discount_percentage) if line.qty != 0 else 0,
                    })
                    if line.qty < 0:
                        line.update({
                            'boo_phan_bo_price_total': 0,
                            'boo_total_discount': -total_global_discount,
                            'boo_total_discount_percentage': -abs(boo_total_discount_percentage),
                        })
                elif line.product_id.available_in_pos:
                    line.update({
                        'boo_phan_bo_price_total': 0,
                        'boo_total_discount': 0,
                        'boo_total_discount_percentage': 0
                    })
                    if not line.program_id and not line.is_line_gift_card and not line.is_refund_gift_card() and not line.s_is_loyalty_reward_line:
                        # if line.price_subtotal_incl < total_global_discount / total_qty:
                        #     boo_total_discount = line.price_subtotal_incl
                        # else:
                        #     boo_total_discount = total_global_discount / total_qty
                        # boo_total_discount_percentage = (boo_total_discount / total_discount) * 100
                        if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                            if line.qty < 0 and refund_price_total_pos_negative != 0:
                                boo_total_discount_percentage = refund_total_discount_negative * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / refund_price_total_pos_negative)
                            if line.qty > 0 and refund_price_total_pos_positive != 0:
                                boo_total_discount_percentage = refund_total_discount_positive * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / refund_price_total_pos_positive)
                            # if refund_price_total_pos != 0:
                            #     boo_total_discount_percentage = refund_total_discount * (
                            #             line.price_unit * line.qty / refund_price_total_pos)
                        else:
                            if price_total_pos != 0:
                                boo_total_discount_percentage = total_discount * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / price_total_pos)
                        # phan bo tren sp = gia don hang - gia sp
                        total_global_discount = 0
                        if 0 <= line.price_unit < line.s_lst_price:
                            total_global_discount = abs((line.s_lst_price - line.price_unit) * line.qty)
                        # total_global_discount = (line.product_id.lst_price - line.price_unit)*line.qty + (line.qty * line.price_unit) * line.discount / 100
                        if line.discount > 0:
                            total_global_discount = total_global_discount + (
                                    line.qty * line.price_unit) * line.discount / 100
                        # product_free_lines = rec.order_id.lines.filtered(lambda
                        #                                                      l: l.program_id and l.program_id.reward_type == 'product' and l.program_id.reward_product_id == line.product_id)
                        # if len(product_free_lines) > 0:
                        #     for line in product_free_lines:
                        #         pos_order_line = self.env['pos.order.line'].sudo().browse(line)
                        #         if pos_order_line:
                        #             total_global_discount += line.price_unit
                        # total_global_discount -= boo_total_discount
                        total_qty -= 1
                        line.update({
                            'boo_phan_bo_price_total': line.price_subtotal_incl - boo_total_discount_percentage,
                            'boo_total_discount': total_global_discount,
                            'boo_total_discount_percentage': format(round(boo_total_discount_percentage, 0), '.2f')
                        })
                        if line.qty < 0:
                            line.update({
                                'boo_phan_bo_price_total': line.price_subtotal_incl - boo_total_discount_percentage,
                                'boo_total_discount': -total_global_discount,
                                'boo_total_discount_percentage': -boo_total_discount_percentage if boo_total_discount_percentage > 0 else boo_total_discount_percentage
                            })

    # check giftcard doi voi order cancel
    def is_refund_gift_card(self):
        for rec in self:
            if rec.refunded_orderline_id and rec.refunded_orderline_id.is_line_gift_card:
                return True
            else:
                return False

    @api.model
    def create(self, values):
        res = super(SPosOrderLineInherit, self).create(values)
        if res.price_unit < 0 and res.qty < 0 and not res.is_program_reward and not res.program_id and res.refunded_orderline_id:
            if res.refunded_orderline_id.is_program_reward and res.refunded_orderline_id.program_id:
                res.sudo().write({
                    'is_program_reward': True,
                    'program_id': res.refunded_orderline_id.program_id.id,
                })
        return res

    # def write(self, values):
    #     if values.get('pack_lot_line_ids'):
    #         for pl in values.get('pack_lot_ids'):
    #             if pl[2].get('server_id'):
    #                 pl[2]['id'] = pl[2]['server_id']
    #                 del pl[2]['server_id']
    #     return super().write(values)

    def _compute_write_date_pos_order_line(self):
        for r in self:
            if r.s_lst_price != r.product_id.lst_price:
                self.env['ir.logging'].sudo().create({
                    'name': '_compute_write_date_pos_order_line',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': 'POS Order: ' + r.order_id.name + ', POS Order Line ID: ' + str(r.id),
                    'func': '_compute_write_date_pos_order_line',
                    'line': '0',
                })

    def _compute_boo_discount_pos_order_line(self):
        # Compute lại chiết khấu của những line SP có giá trong bảng giá = 0 hoặc có áp dụng chiết khấu line
        pos_order_line_price_list_ids = self.search(
            [('price_unit', '=', 0), ('s_lst_price', '!=', 0), ('product_id.detailed_type', '=', 'product'), ('create_date', '>=', '2023/08/26 00:00')])
        pos_order_line_has_discount_ids = self.search([('discount', '>', 0), ('product_id.detailed_type', '=', 'product'), ('create_date', '>=', '2023/08/26 00:00')])
        pos_order_line_ids = pos_order_line_price_list_ids + pos_order_line_has_discount_ids
        if pos_order_line_ids:
            pos_order_line_ids._compute_boo_total_discount()

    def action_compute_boo_total_discount(self):
        for rec in self:
            total_qty = 0
            # total discount ko tinh sp duoc tang
            total_global_discount = 0
            refund_total_global_discount_positive = 0
            refund_total_global_discount_negative = 0
            # total discount tinh sp duoc tang, san pham dac biet
            total_discount = 0
            refund_total_discount_positive = 0
            refund_total_discount_negative = 0
            price_total_pos = 0
            refund_price_total_pos_positive = 0
            refund_price_total_pos_negative = 0
            for line in rec.order_id.lines:
                if not line.product_id.available_in_pos and not line.is_reward_product() and line.product_id.detailed_type == 'service':
                    if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0) or line.is_line_cheapest_refund:
                        if line.refunded_orderline_id and line.qty > 0 and rec.order_id.is_cancel_order:
                            refund_total_global_discount_positive += abs(line.price_subtotal_incl)
                            refund_total_discount_positive += abs(line.price_subtotal_incl)
                        else:
                            refund_total_global_discount_negative += line.price_subtotal_incl
                            refund_total_discount_negative += line.price_subtotal_incl
                    else:
                        total_global_discount += line.price_subtotal_incl
                        total_discount += line.price_subtotal_incl
                # ctkm, coupon, giftcard
                elif line.program_id or line.is_line_gift_card or line.is_refund_gift_card():
                    if not line.is_reward_product():
                        if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                            if line.refunded_orderline_id and line.qty > 0 and rec.order_id.is_cancel_order:
                                refund_total_discount_positive += abs(line.price_subtotal_incl)
                            else:
                                refund_total_discount_negative += line.price_subtotal_incl
                        else:
                            total_discount += line.price_subtotal_incl
                elif line.product_id.available_in_pos and not line.is_free_product:
                    total_qty += 1
                    if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                        if line.refunded_orderline_id and line.qty > 0 and rec.order_id.is_cancel_order:
                            refund_price_total_pos_positive += line.price_subtotal_incl
                        else:
                            refund_price_total_pos_negative += line.price_subtotal_incl
                    else:
                        price_total_pos += line.price_subtotal_incl
            if total_qty == 0:
                total_qty = 1
            total_global_discount = -total_global_discount
            total_discount = -total_discount
            order_lines = rec.order_id.lines.sorted(lambda x: x.price_subtotal_incl)
            for line in order_lines:
                boo_total_discount = 0
                boo_total_discount_percentage = 0
                # if total_discount > 0:
                if line.is_free_product:
                    boo_total_discount = line.get_discount_free_product()
                    boo_total_discount_percentage = abs(boo_total_discount)
                    if line.qty < 0:
                        # Chi co line san pham duoc tang - truong hop CTKM tang nhieu san pham
                        free_product_lines = order_lines.filtered(
                            lambda l: not l.is_free_product and l.product_id.detailed_type != 'service' and l.qty < 0)
                        free_product_price_total_pos = sum(order_lines.filtered(
                            lambda l: l.is_free_product and l.product_id.detailed_type != 'service' and l.qty < 0).mapped(
                            'price_subtotal_incl'))
                        total_discount_free_product = sum(order_lines.filtered(
                            lambda
                                l: not l.is_reward_product() and l.product_id.detailed_type == 'service' and l.qty < 0).mapped(
                            'price_subtotal_incl'))
                    else:
                        free_product_lines = order_lines.filtered(
                            lambda l: not l.is_free_product and l.product_id.detailed_type != 'service' and l.qty > 0)
                        free_product_price_total_pos = sum(order_lines.filtered(
                            lambda l: l.is_free_product and l.product_id.detailed_type != 'service' and l.qty > 0).mapped(
                            'price_subtotal_incl'))
                        total_discount_free_product = sum(order_lines.filtered(
                            lambda
                                l: not l.is_reward_product() and l.product_id.detailed_type == 'service' and l.qty > 0).mapped(
                            'price_subtotal_incl'))
                    total_global_discount = 0
                    if 0 <= line.price_unit < line.s_lst_price:
                        total_global_discount = abs((line.s_lst_price - line.price_unit) * line.qty)
                    if len(free_product_lines) == 0:
                        if free_product_price_total_pos != 0:
                            # sp duoc tang hoan tien
                            if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                                boo_total_discount_percentage += abs((total_discount_free_product * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / free_product_price_total_pos)))
                            else:
                                boo_total_discount_percentage += abs(total_discount_free_product * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / free_product_price_total_pos))
                        else:
                            boo_total_discount_percentage = abs(boo_total_discount) + abs(total_discount_free_product)
                    else:
                        if line.qty < 0:
                            boo_total_discount_percentage = boo_total_discount
                    boo_total_discount_percentage_value = 0
                    if line.qty != 0:
                        boo_total_discount_percentage_value = abs(boo_total_discount_percentage)
                    self._cr.execute("""UPDATE pos_order_line SET boo_phan_bo_price_total = 0 WHERE id = %s""",
                                     (line.id,))
                    self._cr.execute("""UPDATE pos_order_line SET boo_total_discount = %s WHERE id = %s""",
                                     (abs(total_global_discount), line.id))
                    self._cr.execute("""UPDATE pos_order_line SET boo_total_discount_percentage = %s WHERE id = %s""",
                                     (boo_total_discount_percentage_value, line.id))
                    if line.qty < 0:
                        self._cr.execute("""UPDATE pos_order_line SET boo_phan_bo_price_total = 0 WHERE id = %s""",
                                         (line.id,))
                        self._cr.execute("""UPDATE pos_order_line SET boo_total_discount = %s WHERE id = %s""",
                                         (-total_global_discount, line.id))
                        self._cr.execute(
                            """UPDATE pos_order_line SET boo_total_discount_percentage = %s WHERE id = %s""",
                            (-abs(boo_total_discount_percentage), line.id))
                elif line.product_id.available_in_pos:
                    self._cr.execute("""UPDATE pos_order_line SET boo_phan_bo_price_total = 0 WHERE id = %s""",
                                     (line.id,))
                    self._cr.execute("""UPDATE pos_order_line SET boo_total_discount = 0 WHERE id = %s""",
                                     (line.id,))
                    self._cr.execute("""UPDATE pos_order_line SET boo_total_discount_percentage = 0 WHERE id = %s""",
                                     (line.id,))
                    if not line.program_id and not line.is_line_gift_card and not line.is_refund_gift_card():
                        if line.refunded_orderline_id or (line.sale_order_line_id and line.qty < 0):
                            if line.qty < 0 and refund_price_total_pos_negative != 0:
                                boo_total_discount_percentage = refund_total_discount_negative * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / refund_price_total_pos_negative)
                            if line.qty > 0 and refund_price_total_pos_positive != 0:
                                boo_total_discount_percentage = refund_total_discount_positive * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / refund_price_total_pos_positive)
                        else:
                            if price_total_pos != 0:
                                boo_total_discount_percentage = total_discount * (
                                        ((line.price_unit * line.qty) - (line.price_unit * line.qty) *
                                         line.discount / 100) / price_total_pos)
                        # phan bo tren sp = gia don hang - gia sp
                        total_global_discount = 0
                        if 0 <= line.price_unit < line.s_lst_price:
                            total_global_discount = abs((line.s_lst_price - line.price_unit) * line.qty)
                        if line.discount > 0:
                            total_global_discount = total_global_discount + (
                                    line.qty * line.price_unit) * line.discount / 100
                        total_qty -= 1
                        self._cr.execute("""UPDATE pos_order_line SET boo_phan_bo_price_total = %s WHERE id = %s""",
                                         (line.price_subtotal_incl - boo_total_discount_percentage, line.id))
                        self._cr.execute("""UPDATE pos_order_line SET boo_total_discount = %s WHERE id = %s""",
                                         (total_global_discount, line.id))
                        self._cr.execute(
                            """UPDATE pos_order_line SET boo_total_discount_percentage = %s WHERE id = %s""",
                            (format(round(boo_total_discount_percentage, 0), '.2f'), line.id))
                        if line.qty < 0:
                            boo_total_discount_percentage_value = boo_total_discount_percentage
                            if boo_total_discount_percentage > 0:
                                boo_total_discount_percentage_value = -boo_total_discount_percentage
                            self._cr.execute(
                                """UPDATE pos_order_line SET boo_phan_bo_price_total = %s WHERE id = %s""",
                                (line.price_subtotal_incl - boo_total_discount_percentage, line.id))
                            self._cr.execute("""UPDATE pos_order_line SET boo_total_discount = %s WHERE id = %s""",
                                             (-total_global_discount, line.id))
                            self._cr.execute(
                                """UPDATE pos_order_line SET boo_total_discount_percentage = %s WHERE id = %s""",
                                (boo_total_discount_percentage_value, line.id))

    def get_gift_card_balance_by_order_line_id(self, line_id):
        if line_id:
            order_line_id = self.env['pos.order.line'].sudo().search([('id', '=', line_id)], limit=1)
            if order_line_id:
                gift_card = order_line_id.gift_card_id
                if gift_card:
                    vals = {
                        'gift_card_id': gift_card.id,
                        'gift_card_code': gift_card.code,
                        'gift_card_balance': order_line_id.s_gift_card_balance,
                    }
                    return vals
