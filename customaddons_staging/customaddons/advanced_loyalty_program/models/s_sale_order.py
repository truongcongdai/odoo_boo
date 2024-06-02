import ast
from odoo import fields, models, api


class SSaleOrder(models.Model):
    _inherit = 'sale.order'

    s_sale_point_order = fields.Float(string='Loyalty Points', default=0,copy=False)
    s_is_cal_loyalty_points = fields.Boolean(string='Loyalty Đã tính điểm', default=False,copy=False)
    s_used_reward_point_order = fields.Float(string='Used Reward Points', default=0,copy=False)
    s_is_deducted_reward_points = fields.Boolean(string='Loyalty Đơn hàng đã được trừ điểm', default=False,copy=False)

    def write(self, vals):
        sale_order_status_current = self.sudo().sale_order_status
        ###Tính điểm bị trừ cho khách hàng khi đơn hàng có sử dụng quy đổi điểm
        if self.sudo().partner_id:
            if not self.s_is_deducted_reward_points:
                if not self.is_return_order:
                    s_loyalty_product_reward_ids = self.sudo().order_line.filtered(
                        lambda
                            l: l.product_id.detailed_type == 'service' and l.product_id.s_loyalty_product_reward and l.is_loyalty_reward_line)
                    if len(s_loyalty_product_reward_ids) > 0:
                        spent_points = self.s_get_spent_points_sale(s_loyalty_product_reward_ids)
                        if spent_points:
                            history_points_id = self.env['s.order.history.points'].sudo().create([{
                                'sale_order_id': self.sudo().id,
                                'ly_do': 'Điểm trên đơn hàng ' + self.sudo().name,
                                'diem_cong': spent_points,
                                'res_partner_id': self.sudo().partner_id.id
                            }])
                            self.sudo().partner_id.update({
                                'loyalty_points': self.sudo().partner_id.loyalty_points + spent_points
                            })
                            vals.update({
                                's_is_deducted_reward_points': True,
                                's_used_reward_point_order': spent_points
                            })
            ###Tính điểm cho khách hàng khi hoàn thành đơn hàng và có loyalty program áp dụng cho đơn hàng
            if not self.s_is_cal_loyalty_points and vals.get('state') == 'sale':
                loyalty_program_id = self.env['loyalty.program'].sudo().search([('is_apply_so', '=', True)], limit=1)
                if loyalty_program_id:
                    # Cong diem khi hoan thanh don hang
                    won_points = self._cal_loyalty_points_sale(loyalty_program_id)
                    if won_points:
                        if won_points != 0:
                            s_sale_point_order = won_points - abs(self.s_used_reward_point_order)
                            vals.update({
                                's_is_cal_loyalty_points': True,
                                's_sale_point_order': s_sale_point_order
                            })
                            # self._cr.execute(
                            #     """UPDATE sale_order SET s_is_cal_loyalty_points = True, s_sale_point_order = %s WHERE id = %s""",
                            #     (s_sale_point_order, rec.id))
        res = super(SSaleOrder, self).write(vals)
        for rec in self:
            if rec.partner_id:
                ###Tính điểm cho khách hàng khi hoàn thành đơn hàng và có loyalty program áp dụng cho đơn hàng
                if vals.get('completed_date') or (
                        vals.get('sale_order_status') == 'hoan_thanh' and rec.is_return_order) or (
                        vals.get('sale_order_status') == 'hoan_thanh' and (rec.source_id.id == self.env.ref(
                        'advanced_sale.utm_source_sale').id or rec.source_id.id == self.env.ref(
                        'advanced_sale.utm_source_sell_wholesale').id)):
                    if rec.sale_order_status in ['hoan_thanh', 'hoan_thanh_1_phan']:
                        loyalty_points = 0
                        amount_total = 0
                        if not rec.is_return_order:
                            for line in rec.order_line:
                                if line.product_id.detailed_type != 'service':
                                    if line.s_loyalty_point_lines:
                                        loyalty_points += line.s_loyalty_point_lines * line.qty_delivered / line.product_uom_qty
                                    if 0 < line.price_unit < line.s_lst_price:
                                        amount_total += round(line.s_lst_price) * line.qty_delivered - (
                                                round(int(line.boo_total_discount_percentage)) + round(
                                            int(line.boo_total_discount))) * line.qty_delivered / line.product_uom_qty
                                    else:
                                        amount_total += round(line.price_unit) * line.qty_delivered - (
                                                round(int(line.boo_total_discount_percentage)) + round(
                                            int(line.boo_total_discount))) * line.qty_delivered / line.product_uom_qty
                        else:
                            for line in rec.order_line:
                                if line.product_id.detailed_type != 'service':
                                    if line.s_loyalty_point_lines and line.refunded_orderline_id:
                                        loyalty_points += line.s_loyalty_point_lines * line.product_uom_qty / line.refunded_orderline_id.product_uom_qty
                                    if not rec.return_order_id.is_magento_order:
                                        if 0 < line.price_unit < line.s_lst_price:
                                            amount_total += round(line.s_lst_price) * line.product_uom_qty - (
                                                        round(int(line.boo_total_discount_percentage)) - round(
                                                    int(line.boo_total_discount)))
                                        else:
                                            amount_total += round(line.price_unit) * line.product_uom_qty - (
                                                        round(int(line.boo_total_discount_percentage)) - round(
                                                    int(line.boo_total_discount)))
                            if rec.return_order_id.is_magento_order:
                                qty_product_return = abs(sum(rec.order_line.filtered(lambda r: r.is_delivery == False and r.is_line_coupon_program == False and r.is_loyalty_reward_line == False).mapped('product_uom_qty')))
                                qty_product_so_original = abs(sum(rec.return_order_id.order_line.filtered(lambda r: r.is_delivery == False and r.is_line_coupon_program == False and r.is_loyalty_reward_line == False).mapped('product_uom_qty')))
                                if qty_product_return == qty_product_so_original:
                                    if rec.s_used_reward_point_order < 0:
                                        rec.s_sale_point_order = 0
                                        rec.partner_id.sudo().update({
                                            'loyalty_points': rec.partner_id.loyalty_points + abs(
                                                rec.s_used_reward_point_order)
                                        })
                                        self.env['s.order.history.points'].sudo().create([{
                                            'sale_order_id': rec.id,
                                            'ly_do': 'Điểm trên đơn hàng ' + rec.name,
                                            'diem_cong': abs(rec.s_used_reward_point_order),
                                            'res_partner_id': rec.partner_id.id
                                        }])
                        if loyalty_points != 0:
                            rec.s_sale_point_order = loyalty_points
                            self.env['s.order.history.points'].sudo().create([{
                                'sale_order_id': rec.id,
                                'ly_do': 'Điểm trên đơn hàng ' + rec.name,
                                'diem_cong': loyalty_points,
                                'res_partner_id': rec.partner_id.id
                            }])
                            rec.partner_id.sudo().update({
                                'loyalty_points': rec.partner_id.loyalty_points + rec.s_sale_point_order,
                                'total_period_revenue': rec.partner_id.total_period_revenue + amount_total,
                                'total_reality_revenue': rec.partner_id.total_period_revenue + amount_total
                            })
                    elif rec.sale_order_status in ['huy', 'giao_hang_that_bai']:
                        if rec.s_used_reward_point_order < 0:
                            rec.s_sale_point_order = 0
                            rec.partner_id.sudo().update({
                                'loyalty_points': rec.partner_id.loyalty_points + abs(rec.s_used_reward_point_order)
                            })
                            self.env['s.order.history.points'].sudo().create([{
                                'sale_order_id': rec.id,
                                'ly_do': 'Điểm trên đơn hàng ' + rec.name,
                                'diem_cong': abs(rec.s_used_reward_point_order),
                                'res_partner_id': rec.partner_id.id
                            }])
        return res

    def _cal_loyalty_points_sale(self, loyalty_program_id):
        for rec in self:
            won_points = 0
            if loyalty_program_id:
                param_order_id = {
                    'order_type': 'sale_order',
                    'order_id': rec.id,
                    'loyalty_program_id': loyalty_program_id.id,
                    'partner_id': rec.partner_id.id,
                    'customer_rank': rec.partner_id.related_customer_ranked.id,
                    'amount_total': rec.amount_total,
                    'date_order': rec.date_order.date(),
                    'completed_date': rec.completed_date.date() if rec.completed_date else False,
                    'order_line': [{
                        'id': line.id,
                        'product_id': line.product_id,
                        'price_total': line.price_total,
                        'qty_delivered': line.qty_delivered,
                        'price_unit': line.price_unit,
                        'boo_total_discount': line.boo_total_discount,
                        'boo_total_discount_percentage': line.boo_total_discount_percentage,
                        's_lst_price': line.s_lst_price,
                        'product_uom_qty': line.product_uom_qty,
                        'refunded_orderline_id': line.refunded_orderline_id,
                        'is_loyalty_reward_line': line.is_loyalty_reward_line,
                        's_refund_loyalty_point_line': line.refunded_orderline_id.s_loyalty_point_lines, }
                        for line in rec.order_line],
                    's_is_deducted_reward_points': rec.s_is_deducted_reward_points,
                    's_used_reward_point_order': rec.s_used_reward_point_order,
                    's_sale_point_order': rec.s_sale_point_order,
                }
                if param_order_id:
                    won_points = loyalty_program_id.s_get_won_points_sale(param_order_id)
            return won_points

    def s_get_spent_points_sale(self, s_loyalty_product_reward_ids):
        spent_points = 0
        for line in s_loyalty_product_reward_ids:
            if not line.refunded_orderline_id:
                spent_points -= line.s_redeem_amount
            else:
                spent_points += line.s_redeem_amount
        return spent_points

    def create_return_sale_order(self):
        res = super(SSaleOrder, self).create_return_sale_order()
        if res.get('res_id'):
            return_sale_order = self.browse([res.get('res_id')])
            if return_sale_order:
                for line in return_sale_order.order_line:
                    if line.refunded_orderline_id:
                        line.is_loyalty_reward_line = line.refunded_orderline_id.is_loyalty_reward_line
                        line.s_loyalty_point_lines = line.refunded_orderline_id.s_loyalty_point_lines
                        line.s_redeem_amount = line.refunded_orderline_id.s_redeem_amount
                if return_sale_order.return_order_id.s_used_reward_point_order != 0:
                    return_sale_order.s_used_reward_point_order = return_sale_order.return_order_id.s_used_reward_point_order
        return res
