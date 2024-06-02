import math

from odoo import fields, models, api, _


class SLoyaltyPosOrderLineInherit(models.Model):
    _inherit = 'pos.order.line'

    s_loyalty_program_id = fields.Many2one('loyalty.reward', 'Chương trình loyalty')
    s_is_loyalty_reward_line = fields.Boolean('Là line loyalty reward')
    loyalty_points = fields.Float(string='Loyalty points')
    s_is_gift_product_reward = fields.Boolean('Là line gift product reward')

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

    def refund_loyalty_points(self, refunded_orderline_id, refund_all):
        list_order_line = []
        if refunded_orderline_id:
            for rec in refunded_orderline_id:
                refunded_qty = 0
                loyalty_points = 0
                if rec.get('qty'):
                    refunded_qty = - rec.get('qty')
                order_line = rec.get('orderline')
                if order_line:
                    line = self.sudo().search([('id', '=', order_line.get('id'))], limit=1)
                    if line:
                        if refund_all:
                            loyalty_points = (line.loyalty_points / line.qty) * refunded_qty
                        else:
                            if not line.s_loyalty_program_id:
                                loyalty_points = (line.loyalty_points / line.qty) * refunded_qty
                        list_order_line.append(
                            {
                                'refunded_orderline_id': order_line.get('id'),
                                'loyalty_points': loyalty_points,
                            }
                        )
        return list_order_line