from odoo import fields, models, api, _


class SSaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    is_loyalty_reward_line = fields.Boolean(string='Là line loyalty program', default=False)
    s_loyalty_point_lines = fields.Float(string='Loyalty Point Lines', default=0)
    s_redeem_amount = fields.Float(string='Redeem Amount', default=0)
    s_chanel_discount = fields.Float(string='Chanel Discount')
    s_crm_discount = fields.Float(string='CRM Discount')
    s_hr_discount = fields.Float(string='HR Discount')
    s_type_discount = fields.Selection([
        ('chanel', 'Channel'),
        ('crm', 'CRM'),
        ('hr', 'HR')
    ], string='Loại Discount', compute='_compute_type_discount_sale', store=True)

    @api.depends('s_chanel_discount', 's_crm_discount', 's_hr_discount')
    def _compute_type_discount_sale(self):
        for rec in self:
            rec.s_type_discount = None
            if rec.coupon_program_id and rec.coupon_program_id.reward_type == 'discount' and rec.coupon_program_id.s_type_discount and rec.product_id.detailed_type == 'service':
                if rec.coupon_program_id.s_type_discount == 'chanel':
                    rec.s_type_discount == 'chanel'
                elif rec.coupon_program_id.s_type_discount == 'crm':
                    rec.s_type_discount == 'crm'
                elif rec.coupon_program_id.s_type_discount == 'hr':
                    rec.s_type_discount = 'hr'
            elif rec.gift_card_id and rec.gift_card_id.s_type_discount and not rec.gift_card_id.is_not_calculate_amount:
                if rec.gift_card_id.s_type_discount == 'chanel':
                    rec.s_type_discount = 'chanel'
                elif rec.gift_card_id.s_type_discount == 'crm':
                    rec.s_type_discount = 'crm'
                elif rec.gift_card_id.s_type_discount == 'hr':
                    rec.s_type_discount = 'hr'
            elif rec.is_loyalty_reward_line:
                rec.s_type_discount = 'crm'

    @api.depends('s_chanel_discount', 's_crm_discount', 's_hr_discount')
    def _compute_type_discount_sale(self):
        res = super(SSaleOrderLineInherit, self)._compute_type_discount_sale()
        for rec in self:
            if rec.is_loyalty_reward_line:
                rec.s_type_discount = 'crm'
        return res

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'm2_total_line_discount',
                 'm2_is_global_discount')
    def _compute_boo_total_discount(self):
        total_discount = 0
        refund_total_discount = 0
        total_global_discount = 0
        refund_total_global_discount = 0
        total_qty = 0
        is_chanel_discount = 0
        is_crm_discount = 0
        is_hr_discount = 0
        refund_chanel_discount = 0
        refund_crm_discount = 0
        refund_hr_discount = 0
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
            elif e.coupon_program_id or e.gift_card_id or e.is_line_coupon_program or e.is_loyalty_reward_line:
                free_product = e.is_free_product()
                if free_product or not self[0].order_id.is_magento_order or not self[0].order_id.is_invisible_ecommerce:
                    if e.refunded_orderline_id:
                        refund_total_discount += e.price_total
                        if e.coupon_program_id:
                            if e.coupon_program_id.reward_type == 'discount' and e.coupon_program_id.s_type_discount and e.product_id.detailed_type == 'service':
                                if e.coupon_program_id.s_type_discount == 'chanel':
                                    refund_chanel_discount += e.price_total
                                elif e.coupon_program_id.s_type_discount == 'crm':
                                    refund_crm_discount += e.price_total
                                elif e.coupon_program_id.s_type_discount == 'hr':
                                    refund_hr_discount += e.price_total
                        elif e.gift_card_id:
                            if e.gift_card_id.s_type_discount and not e.gift_card_id.is_not_calculate_amount:
                                if e.gift_card_id.s_type_discount == 'chanel':
                                    refund_chanel_discount += e.price_total
                                elif e.gift_card_id.s_type_discount == 'crm':
                                    refund_crm_discount += e.price_total
                                elif e.gift_card_id.s_type_discount == 'hr':
                                    refund_hr_discount += e.price_total
                        elif e.is_loyalty_reward_line:
                            refund_crm_discount += e.price_total
                    else:
                        total_discount += e.price_total
                        if e.coupon_program_id:
                            if e.coupon_program_id.reward_type == 'discount' and e.coupon_program_id.s_type_discount and e.product_id.detailed_type == 'service':
                                if e.coupon_program_id.s_type_discount == 'chanel':
                                    is_chanel_discount += e.price_total
                                elif e.coupon_program_id.s_type_discount == 'crm':
                                    is_crm_discount += e.price_total
                                elif e.coupon_program_id.s_type_discount == 'hr':
                                    is_hr_discount += e.price_total
                        elif e.gift_card_id:
                            if e.gift_card_id.s_type_discount and not e.gift_card_id.is_not_calculate_amount:
                                if e.gift_card_id.s_type_discount == 'chanel':
                                    is_chanel_discount += e.price_total
                                elif e.gift_card_id.s_type_discount == 'crm':
                                    is_crm_discount += e.price_total
                                elif e.gift_card_id.s_type_discount == 'hr':
                                    is_hr_discount += e.price_total
                        elif e.is_loyalty_reward_line:
                            is_crm_discount += e.price_total

            # SO line
            # else:
            #     total_qty += e.product_uom_qty
            # total_discount += -e.m2_total_line_discount
        if total_qty == 0:
            total_qty = 1
        total_global_discount = -total_global_discount
        # tong discount SO tinh ca discount tung line va discount ca SO
        total_discount = -total_discount
        is_chanel_discount = -is_chanel_discount
        is_crm_discount = -is_crm_discount
        is_hr_discount = -is_hr_discount
        for line in self[0].order_id.order_line:
            boo_total_discount = 0
            boo_total_discount_percentage = 0
            price_total_so = 0
            refund_price_total_so = 0
            chanel_discount = 0
            crm_discount = 0
            hr_discount = 0
            line.update({
                'boo_phan_bo_price_total': 0,
                'boo_total_discount': 0,
                'boo_total_discount_percentage': 0,
                's_chanel_discount': 0,
                's_crm_discount': 0,
                's_hr_discount': 0
            })
            if line.refunded_orderline_id:
                refund_price_total_so = sum(
                    [line.price_unit * line.product_uom_qty for line in self[0].order_id.order_line if
                     not line.m2_is_global_discount and not line.coupon_program_id and not line.is_delivery and not line.gift_card_id
                     and not line.is_ecommerce_reward_line and not line.is_line_coupon_program and line.refunded_orderline_id and not line.is_loyalty_reward_line])
            else:
                price_total_so = sum([line.price_unit * line.product_uom_qty for line in self[0].order_id.order_line if
                                      not line.m2_is_global_discount and not line.coupon_program_id and not line.is_delivery and not line.gift_card_id
                                      and not line.is_ecommerce_reward_line and not line.is_line_coupon_program and not line.refunded_orderline_id and not line.is_loyalty_reward_line])
            # if total_discount > 0:
            if self[0].order_id.is_magento_order:
                # boo_total_discount = (line.product_id.lst_price - line.price_unit)*line.product_uom_qty + line.m2_total_line_discount
                if not line.is_product_reward:
                    boo_total_discount = (line.s_lst_price - line.price_unit) * line.product_uom_qty
                else:
                    boo_total_discount = (-line.s_lst_price - line.price_unit) * line.product_uom_qty
                if line.price_unit > line.s_lst_price:
                    boo_total_discount = 0
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
            # boo_total_discount = total_global_discount / total_qty * line.product_uom_qty + line.m2_total_line_discount
            # boo_total_discount_percentage = boo_total_discount / total_discount * 100
            if line.refunded_orderline_id:
                if refund_price_total_so != 0 and not line.is_free_product() and not line.is_delivery and not line.is_line_coupon_program and not line.is_loyalty_reward_line:
                    boo_total_discount_percentage = refund_total_discount * (
                            ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) *
                             line.discount / 100) / refund_price_total_so)
                    chanel_discount = refund_chanel_discount * (
                            ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) *
                             line.discount / 100) / refund_price_total_so)
                    crm_discount = refund_crm_discount * (
                            ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) *
                             line.discount / 100) / refund_price_total_so)
                    hr_discount = refund_hr_discount * (
                            ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) *
                             line.discount / 100) / refund_price_total_so)
            else:
                if price_total_so != 0:
                    if not line.is_free_product() and not line.is_delivery and not line.is_line_coupon_program and not line.coupon_program_id and not line.gift_card_id and not line.is_loyalty_reward_line:
                        if self[0].order_id.is_magento_order:
                            boo_total_discount_percentage = total_discount * (((
                                                                                           line.price_unit * line.product_uom_qty) - (
                                                                                           line.price_unit * line.product_uom_qty) * line.discount / 100) / price_total_so)
                            chanel_discount = is_chanel_discount * (((line.price_unit * line.product_uom_qty) - (
                                        line.price_unit * line.product_uom_qty) * line.discount / 100) / price_total_so)
                            crm_discount = is_crm_discount * (((line.price_unit * line.product_uom_qty) - (
                                        line.price_unit * line.product_uom_qty) * line.discount / 100) / price_total_so)
                            hr_discount = is_hr_discount * (((line.price_unit * line.product_uom_qty) - (
                                        line.price_unit * line.product_uom_qty) * line.discount / 100) / price_total_so)
                        else:
                            boo_total_discount_percentage = total_discount * (
                                    ((line.price_unit * line.product_uom_qty) - (
                                            line.price_unit * line.product_uom_qty) *
                                     line.discount / 100) / price_total_so)
                            chanel_discount = is_chanel_discount * (
                                    ((line.price_unit * line.product_uom_qty) - (
                                            line.price_unit * line.product_uom_qty) *
                                     line.discount / 100) / price_total_so)
                            crm_discount = is_crm_discount * (
                                    ((line.price_unit * line.product_uom_qty) - (
                                            line.price_unit * line.product_uom_qty) *
                                     line.discount / 100) / price_total_so)
                            hr_discount = is_hr_discount * (
                                    ((line.price_unit * line.product_uom_qty) - (
                                            line.price_unit * line.product_uom_qty) *
                                     line.discount / 100) / price_total_so)

            if not line.m2_is_global_discount:
                line.update({
                    'boo_phan_bo_price_total': line.price_total,
                    'boo_total_discount': abs(boo_total_discount),
                    'boo_total_discount_percentage': abs(boo_total_discount_percentage) if not line.is_product_reward
                    else boo_total_discount_percentage,
                    's_chanel_discount': chanel_discount,
                    's_crm_discount': crm_discount,
                    's_hr_discount': hr_discount,
                })
                if line.product_uom_qty < 0:
                    line.update({
                        'boo_phan_bo_price_total': line.price_total,
                        'boo_total_discount': -boo_total_discount,
                        'boo_total_discount_percentage': -boo_total_discount_percentage,
                        's_chanel_discount': -chanel_discount,
                        's_crm_discount': -crm_discount,
                        's_hr_discount': -hr_discount,
                    })
                # line.update({
                #     'boo_phan_bo_price_total': line.price_total,
                #     'boo_total_discount': line.m2_total_line_discount + boo_total_discount,
                #     'boo_total_discount_percentage': boo_total_discount_percentage,
                # })

    def read_converted(self):
        res = super(SSaleOrderLineInherit, self).read_converted()
        for r in res:
            sale_order_line_id = self.search([('id', '=', r.get('id'))], limit=1)
            if sale_order_line_id:
                r['sol_loyalty_point'] = sale_order_line_id.s_loyalty_point_lines
                if sale_order_line_id.is_loyalty_reward_line:
                    r['is_loyalty_reward_line'] = sale_order_line_id.is_loyalty_reward_line
                    r['s_redeem_amount'] = sale_order_line_id.s_redeem_amount
        return res
