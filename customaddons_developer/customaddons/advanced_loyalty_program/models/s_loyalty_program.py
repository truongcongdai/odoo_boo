from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SAdvancedLoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    s_point_exchange = fields.Integer(string='Điểm quy đổi', required=True,
                                      help='Điền tỷ lệ đổi điểm thành tiền của chương trình', default=1)
    s_monetary_exchange = fields.Integer(string='Tiền quy đổi', required=True, default=1)
    is_apply_so = fields.Boolean(string='Áp dụng cho Sale Order')
    zns_template_id = fields.Many2one('zns.template', string='ZNS Template')
    is_refund_loyalty_points = fields.Boolean(string='Áp dụng cho đơn đổi trả sử dụng logic customize')

    @api.onchange('s_exchange_money', 's_monetary_exchange', 's_point_exchange')
    def _onchange_s_exchange_money(self):
        for rec in self:
            if rec.s_monetary_exchange <= 0:
                raise ValidationError('Tiền quy đổi phải lớn hơn 0')
            elif rec.s_point_exchange < 0:
                raise ValidationError('Điểm quy đổi phải lớn hơn 0')

    @api.constrains('is_apply_so')
    def s_contrains_apply_so(self):
        for rec in self:
            if rec.is_apply_so:
                loyalty_program_id = self.search([('is_apply_so', '=', True), ('id', '!=', rec.id)])
                if len(loyalty_program_id):
                    raise ValidationError(
                        'Đã tồn tại chương trình khách hàng thân thiết áp dụng cho Sale Order: %s' % loyalty_program_id.name)

    def s_get_won_points_sale(self, order_id):
        for rec in self:
            if order_id:
                if order_id.get('order_line'):
                    order_line = order_id.get('order_line')
                    total_points = 0
                    spent_points = 0
                    customer_rank = order_id.get('customer_rank')
                    date_order = order_id.get('date_order')
                    for line in order_line:
                        order_type = order_id.get('order_type')
                        product_id = line.get('product_id')
                        price_total = line.get('price_total')
                        qty_delivered = line.get('qty_delivered')
                        price_unit = line.get('price_unit')
                        boo_total_discount = line.get('boo_total_discount')
                        boo_total_discount_percentage = line.get('boo_total_discount_percentage')
                        s_lst_price = line.get('s_lst_price')
                        product_uom_qty = line.get('product_uom_qty')
                        refunded_orderline_id = line.get('refunded_orderline_id')
                        is_loyalty_reward_line = line.get('is_loyalty_reward_line')
                        s_refund_loyalty_point_line = line.get('s_refund_loyalty_point_line')
                        list_point = []
                        line_total_amount = 0
                        if not refunded_orderline_id and product_id.detailed_type != 'service':
                            if 0 < price_unit < s_lst_price:
                                line_total_amount = round(s_lst_price) * product_uom_qty - (
                                        round(int(boo_total_discount_percentage)) + round(
                                    int(boo_total_discount)))
                            else:
                                line_total_amount = round(price_unit) * product_uom_qty - (
                                            round(int(boo_total_discount_percentage)) + round(
                                        int(boo_total_discount)))
                            for rule_id in rec.rule_ids:
                                rule_points = 0
                                if product_id.id in rule_id.valid_product_ids.ids and product_id.detailed_type != 'service':
                                    ###Tính số tiền cửa từng line
                                    if rule_id.s_rule_type == 'special':
                                        ###TH1.1 không có ngày áp dụng và hạng áp dụng
                                        if not rule_id.s_rule_date_from and not rule_id.s_rule_date_to and not rule_id.s_rule_apply_for:
                                            rule_points += rule_id.points_quantity * product_uom_qty
                                            rule_points += rule_id.points_currency * line_total_amount
                                        ###TH1.2 không có ngày áp dụng và có hạng áp dụng
                                        if not rule_id.s_rule_date_from and not rule_id.s_rule_date_to and rule_id.s_rule_apply_for:
                                            if rule_id.s_rule_apply_for:
                                                if customer_rank in rule_id.s_rule_apply_for.mapped('id'):
                                                    rule_points += rule_id.points_quantity * product_uom_qty
                                                    rule_points += rule_id.points_currency * line_total_amount
                                        ###TH2 Có ngày bắt đầu và không có ngày kết thúc
                                        elif rule_id.s_rule_date_from and not rule_id.s_rule_date_to:
                                            if date_order >= rule_id.s_rule_date_from:
                                                ###TH2.1: Có hạng áp dụng
                                                if rule_id.s_rule_apply_for:
                                                    if customer_rank in rule_id.s_rule_apply_for.mapped('id'):
                                                        rule_points += rule_id.points_quantity * product_uom_qty
                                                        rule_points += rule_id.points_currency * line_total_amount
                                                ###TH2.2: Không có hạng áp dụng
                                                else:
                                                    rule_points += rule_id.points_quantity * product_uom_qty
                                                    rule_points += rule_id.points_currency * line_total_amount
                                        ###TH3 Có ngày kết thúc và không có ngày bắt đầu
                                        elif rule_id.s_rule_date_to and not rule_id.s_rule_date_from:
                                            if date_order <= rule_id.s_rule_date_to:
                                                ###TH3.1: Có hạng áp dụng
                                                if rule_id.s_rule_apply_for:
                                                    if customer_rank in rule_id.s_rule_apply_for.mapped('id'):
                                                        rule_points += rule_id.points_quantity * product_uom_qty
                                                        rule_points += rule_id.points_currency * line_total_amount
                                                ###TH3.2: Không có hạng áp dụng
                                                else:
                                                    rule_points += rule_id.points_quantity * product_uom_qty
                                                    rule_points += rule_id.points_currency * line_total_amount
                                        ###TH4 Có ngày bắt đầu và có ngày kết thúc
                                        elif rule_id.s_rule_date_to and rule_id.s_rule_date_from:
                                            if rule_id.s_rule_date_from <= date_order <= rule_id.s_rule_date_to:
                                                ###TH4.1: Có hạng áp dụng
                                                if rule_id.s_rule_apply_for:
                                                    if customer_rank in rule_id.s_rule_apply_for.mapped('id'):
                                                        rule_points += rule_id.points_quantity * product_uom_qty
                                                        rule_points += rule_id.points_currency * line_total_amount
                                                ###TH4.2: Không có hạng áp dụng
                                                else:
                                                    rule_points += rule_id.points_quantity * product_uom_qty
                                                    rule_points += rule_id.points_currency * line_total_amount
                                        if rule_id.s_multiplication_point > 0:
                                            rule_points = rule_points * rule_id.s_multiplication_point
                                    if rule_id.s_rule_type == 'rule_point':
                                        if len(rule_id.s_rule_point_id):
                                            for rule_point_id in rule_id.s_rule_point_id:
                                                if rule_point_id.s_customer_ranked_id.id == customer_rank:
                                                    loyalty_line = (line_total_amount * rule_point_id.s_proportion_point) / 100
                                                    list_point.append(loyalty_line)
                                list_point.append(rule_points)
                            if list_point:
                                cal_point = max(list_point) + ((line_total_amount / rec.s_monetary_exchange) * rec.s_point_exchange)
                            else:
                                cal_point = ((line_total_amount / rec.s_monetary_exchange) * rec.s_point_exchange)
                            if order_type == 'sale_order':
                                sale_order_line = self.env['sale.order.line'].search([('id', '=', line.get('id'))])
                                if sale_order_line:
                                    sale_order_line.s_loyalty_point_lines = cal_point
                            total_points += cal_point
                        ###TH2: Là line hoàn tiền
                        else:
                            if product_id.detailed_type != 'service' and not is_loyalty_reward_line:
                                spent_points -= s_refund_loyalty_point_line
                                if spent_points:
                                    total_points += spent_points
                    return total_points
