from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SAdvancedRulePoint(models.Model):
    _name = 's.rule.point'

    s_customer_ranked_id = fields.Many2one('s.customer.rank', string='Hạng')
    s_proportion_point = fields.Integer(string='Tỷ lệ tích điểm trên tổng giá trị đơn hàng (%)',
                                        help='Điền % quy đổi điểm trên đơn hàng cho hạng thành viên tương ứng')
    s_loyalty_rule_id = fields.Many2one('loyalty.rule')

    @api.model
    def create(self, vals_list):
        res = super(SAdvancedRulePoint, self).create(vals_list)
        for r in res:
            if r.s_loyalty_rule_id.s_rule_type == 'rule_point':
                rule_points = r.s_loyalty_rule_id.s_rule_point_id
                if rule_points:
                    ranked_id = rule_points.filtered(lambda l: l.s_customer_ranked_id.id == r.s_customer_ranked_id.id)
                    if len(ranked_id) > 1:
                        raise ValidationError('Quy tắc tích điểm đã thiết lập tỉ lệ tích điểm cho hạng %s' % r.s_customer_ranked_id.rank)
        return res

    def write(self, vals_list):
        res = super(SAdvancedRulePoint, self).write(vals_list)
        for rec in self:
            if rec.s_loyalty_rule_id.s_rule_type == 'rule_point':
                rule_points = rec.s_loyalty_rule_id.s_rule_point_id
                if rule_points:
                    ranked_id = rule_points.filtered(lambda l: l.s_customer_ranked_id.id == rec.s_customer_ranked_id.id)
                    if len(ranked_id) > 1:
                        raise ValidationError('Quy tắc tích điểm đã thiết lập tỉ lệ tích điểm cho hạng %s' % rec.s_customer_ranked_id.rank)
        return res
