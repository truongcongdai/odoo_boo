from odoo import fields, models, api, _
import ast
import math
from datetime import datetime



class SPosOrder(models.Model):
    _inherit = 'pos.order'

    s_pos_point_order = fields.Float(string='Stored Loyalty Points', default=0)

    def s_get_won_points_pos(self, order_id, loyalty_program_id):
        if loyalty_program_id:
            order_line = order_id.lines
            s_rule_ranked_point = 0
            customer_rank = order_id.partner_id.customer_ranked
            customer_rank_id = order_id.partner_id.related_customer_ranked.id
            ###Thêm log check trường hợp relate_customer_ranked không có giá trị
            if not customer_rank_id:
                log = {
                    'order_name': order_id.name,
                    'order_id': order_id.id,
                    'relate_customer_ranked': customer_rank_id
                }
                self.env['ir.logging'].sudo().create({
                    'name': 'Check related_customer_ranked ',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(log) if log else None,
                    'func': 'create_res_partner',
                    'line': '0',
                })
            for line in order_line:
                list_point = []
                if line.product_id.detailed_type != 'service' and not line.s_loyalty_program_id:
                    ###Tính số tiền cửa từng line
                    if not line.refunded_orderline_id:
                        line_total_amount = line.price_subtotal - (round(int(line.boo_total_discount_percentage)) + round(int(line.boo_total_discount)))
                        for rule_id in loyalty_program_id.get('rules'):
                            rule_points = 0
                            if line.product_id.id in rule_id.get('valid_product_ids') and line.product_id.detailed_type != 'service':
                                if rule_id.get('s_rule_type') == 'special':
                                    ###TH1.1 không có ngày áp dụng và hạng áp dụng
                                    if not rule_id.get('s_rule_date_from') and not rule_id.get('s_rule_date_to') and not rule_id.get('s_rule_apply_for'):
                                        rule_points += rule_id.get('points_quantity') * line.qty
                                        rule_points += rule_id.get('points_currency') * line.price_subtotal
                                        if rule_id.get('s_multiplication_point') > 0:
                                            rule_points = rule_points * rule_id.get('s_multiplication_point')
                                    ###TH1.2 không có ngày áp dụng và có hạng áp dụng
                                    if not rule_id.get('s_rule_date_from') and not rule_id.get('s_rule_date_to') and rule_id.get('s_rule_apply_for'):
                                        rule_points += rule_id.get('points_quantity') * line.qty
                                        rule_points += rule_id.get('points_currency') * line.price_subtotal
                                        ###Có hạng áp dụng
                                        if rule_id.get('s_rule_apply_for'):
                                            if customer_rank_id in rule_id.get('s_rule_apply_for'):
                                                rule_points += rule_id.get('points_quantity') * line.qty
                                                rule_points += rule_id.get('points_currency') * line.price_subtotal
                                                if rule_id.get('s_multiplication_point') > 0:
                                                    rule_points = rule_points * rule_id.get('s_multiplication_point')
                                    ###TH2 Có ngày bắt đầu và không có ngày kết thúc
                                    elif rule_id.get('s_rule_date_from') and not rule_id.get('s_rule_date_to'):
                                        if order_id.date_order.date() >= datetime.strptime(rule_id.get('s_rule_date_from'), '%Y-%m-%d').date():
                                            ###TH2.1: Có hạng áp dụng
                                            if rule_id.get('s_rule_apply_for'):
                                                if customer_rank_id in rule_id.get('s_rule_apply_for'):
                                                    rule_points += rule_id.get('points_quantity') * line.qty
                                                    rule_points += rule_id.get('points_currency') * line.price_subtotal
                                                    if rule_id.get('s_multiplication_point') > 0:
                                                        rule_points = rule_points * rule_id.get('s_multiplication_point')
                                            ###TH2.2: Không có hạng áp dụng
                                            else:
                                                rule_points += rule_id.get('points_quantity') * line.qty
                                                rule_points += rule_id.get('points_currency') * line.price_subtotal
                                                if rule_id.get('s_multiplication_point') > 0:
                                                    rule_points = rule_points * rule_id.get('s_multiplication_point')
                                    ###TH3 Có ngày kết thúc và không có ngày bắt đầu
                                    elif rule_id.get('s_rule_date_to') and not rule_id.get('s_rule_date_from'):
                                        if order_id.date_order.date() <= datetime.strptime(rule_id.get('s_rule_date_to'), '%Y-%m-%d').date():
                                            ###TH3.1: Có hạng áp dụng
                                            if rule_id.get('s_rule_apply_for'):
                                                if customer_rank_id in rule_id.get('s_rule_apply_for'):
                                                    rule_points += rule_id.get('points_quantity') * line.qty
                                                    rule_points += rule_id.get('points_currency') * line.price_subtotal
                                                    if rule_id.get('s_multiplication_point') > 0:
                                                        rule_points = rule_points * rule_id.get('s_multiplication_point')
                                            ###TH3.2: Không có hạng áp dụng
                                            else:
                                                rule_points += rule_id.get('points_quantity') * line.qty
                                                rule_points += rule_id.get('points_currency') * line.price_subtotal
                                                if rule_id.get('s_multiplication_point') > 0:
                                                    rule_points = rule_points * rule_id.get('s_multiplication_point')
                                    ###TH4 Có ngày bắt đầu và có ngày kết thúc
                                    elif rule_id.get('s_rule_date_to') and rule_id.get('s_rule_date_from'):
                                        if datetime.strptime(rule_id.get('s_rule_date_from'),
                                                             '%Y-%m-%d').date() <= order_id.date_order.date() <= datetime.strptime(
                                                rule_id.get('s_rule_date_to'), '%Y-%m-%d').date():
                                            ###TH4.1: Có hạng áp dụng
                                            if rule_id.get('s_rule_apply_for'):
                                                if customer_rank_id in rule_id.get('s_rule_apply_for'):
                                                    rule_points += rule_id.get('points_quantity') * line.qty
                                                    rule_points += rule_id.get('points_currency') * line.price_subtotal
                                                    if rule_id.get('s_multiplication_point') > 0:
                                                        rule_points = rule_points * rule_id.get('s_multiplication_point')
                                            ###TH4.2: Không có hạng áp dụng
                                            else:
                                                rule_points += rule_id.get('points_quantity') * line.qty
                                                rule_points += rule_id.get('points_currency') * line.price_subtotal
                                                if rule_id.get('s_multiplication_point') > 0:
                                                    rule_points = rule_points * rule_id.get('s_multiplication_point')
                                if rule_id.get('s_rule_type') == 'rule_point':
                                    if len(rule_id.get('s_rule_point_id')):
                                        for rule_point_id in rule_id.get('s_rule_point_id'):
                                            rules_point = self.env['s.rule.point'].sudo().search([('id', '=', rule_point_id)])
                                            if rules_point:
                                                if rules_point.s_customer_ranked_id.rank == customer_rank:
                                                    # s_rule_ranked_point += (line_total_amount * rule_point_id.s_proportion_point) / 100
                                                    loyalty_line = (line_total_amount * rules_point.s_proportion_point) / 100
                                                    list_point.append(loyalty_line)
                                                    break
                            list_point.append(rule_points)
                        ###Tính điểm từ quy đổi tiền
                        if list_point:
                            line.loyalty_points = ((line_total_amount / loyalty_program_id.get('s_monetary_exchange')) * loyalty_program_id.get('s_point_exchange')) + max(list_point)
                        else:
                            line.loyalty_points = ((line_total_amount / loyalty_program_id.get('s_monetary_exchange')) * loyalty_program_id.get('s_point_exchange'))
            return round(sum([vale.loyalty_points for vale in order_line]))

    def s_get_spent_points_pos(self, s_loyalty_product_reward_ids):
        spent_points = 0
        for line in s_loyalty_product_reward_ids:
            if not line.refunded_orderline_id:
                if line.s_loyalty_program_id.reward_type in ('discount', 'gift'):
                    line.loyalty_points -= line.s_loyalty_program_id.point_cost * line.qty
                    spent_points += line.loyalty_points
                elif line.s_loyalty_program_id.reward_type == 'point':
                    line.loyalty_points -= line.s_loyalty_program_id.s_reward_exchange_point * line.qty
                    spent_points += line.loyalty_points
        return spent_points


    @api.model
    def create_from_ui(self, orders, draft=False):
        order_ids = super(SPosOrder, self).create_from_ui(orders, draft)
        for rec in orders:
            apply_loyalty_program = False
            if rec.get('data'):
                if rec.get('data').get('apply_loyalty_program'):
                    apply_loyalty_program = rec.get('data').get('apply_loyalty_program')
            for order in self.sudo().browse([o['id'] for o in order_ids]):
                if apply_loyalty_program:
                    # loyalty_program_id = apply_loyalty_program
                    # if loyalty_program_id:
                    #     ###Tính điểm cho khách hàng khi hoàn thành đơn hàng và có loyalty program áp dụng cho đơn hàng
                    #     won_point = order.s_get_won_points_pos(order, loyalty_program_id)
                    #     ###Tính điểm bị trừ cho khách hàng khi đơn hàng có sử dụng quy đổi reward
                    #     if loyalty_program_id.get('rewards'):
                    #         s_loyalty_product_reward_ids = order.lines.filtered(lambda l: l.s_loyalty_program_id and (
                    #                     l.s_is_loyalty_reward_line or l.s_is_gift_product_reward))
                    #         if s_loyalty_product_reward_ids:
                    #             spent_points = order.s_get_spent_points_pos(s_loyalty_product_reward_ids)
                    if order.loyalty_points:
                        history_points = self.env['s.order.history.points'].sudo().search([('order_id', '=', order.id)])
                        if history_points:
                            history_points.sudo().write({'diem_cong': order.loyalty_points})
                if order.partner_id:
                    order.partner_id.total_period_revenue += order.amount_paid
                    order.partner_id.total_reality_revenue += order.amount_paid
        return order_ids

    @api.model
    def _order_fields(self, ui_order):
        ###Thêm điều kiện vào orderline để tính chiết khấu phân bổ cho line quy đổi điểm
        for line in ui_order.get('lines'):
            for l in line:
                if type(l) is dict:
                    if l.get('reward_id') is not None:
                        reward_id = self.env['loyalty.reward'].sudo().search([('id', '=', l.get('reward_id'))])
                        if reward_id:
                            l['s_loyalty_program_id'] = l.get('reward_id')
                            if reward_id.reward_type in ('point', 'discount'):
                                l['s_is_loyalty_reward_line'] = True
                                l['loyalty_points'] = -l.get('loyalty_points')
                            elif reward_id.reward_type == 'gift':
                                if reward_id.gift_product_id.id == l.get('product_id'):
                                    # l['s_is_loyalty_reward_line'] = True
                                    l['s_is_gift_product_reward'] = True
                                    l['loyalty_points'] = -l.get('loyalty_points')
                    else:
                        product_id = self.env['product.product'].sudo().search([('id', '=', l.get('product_id'))])
                        if product_id:
                            if product_id.detailed_type != 'service':
                                l['loyalty_points'] = l.get('loyalty_points')

        order_fields = super(SPosOrder, self)._order_fields(ui_order)
        return order_fields

    def force_unlink_cancel_order(self):
        self.sudo().partner_id.loyalty_points = self.sudo().partner_id.loyalty_points + self.loyalty_points
        if self.loyalty_points:
            data_points = {
                'diem_cong': -self.loyalty_points,
                'ly_do': 'Xóa đơn hàng hủy',
                'res_partner_id': self.partner_id.id
            }
            self.env['s.order.history.points'].sudo().create([data_points])
        res = super(SPosOrder, self).force_unlink_cancel_order()
        return res


class SPosMakePaymentInherit(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        ###Khi confirm đơn hàng hủy -> trừ doanh thu trong kỳ đi
        res = super(SPosMakePaymentInherit, self).check()
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        if order:
            if order.is_cancel_order:
                if order.partner_id:
                    order.sudo().partner_id.total_period_revenue = order.sudo().partner_id.total_period_revenue + self.amount
        return res
