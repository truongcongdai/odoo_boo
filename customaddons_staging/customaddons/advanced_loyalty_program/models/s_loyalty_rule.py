from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SAdvancedLoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    s_rule_type = fields.Selection([('special', 'Đặc biệt'), ('rule_point', 'Quy tắc tích điểm')], string='Loại quy tắc', default='special')
    s_rule_point_id = fields.One2many('s.rule.point', 's_loyalty_rule_id')
    s_rule_date_to = fields.Date(string='Từ:', help='Thời gian quy tắc đặc biệt hết hiệu lực')
    s_rule_date_from = fields.Date(string='Đến:', help='Thời gian quy tắc đặc biệt bắt đầu có hiệu lực')
    s_multiplication_point = fields.Integer(string='Nhân', help='Điền số muốn nhân với điểm trên đơn hàng', default=1)
    s_rule_apply_for = fields.Many2many('s.customer.rank', string='Áp dụng với',
                                        help='Chọn các hạng thành viên áp dụng cho quy tắc, không chọn sẽ áp dụng cho tất cả')

    @api.onchange('s_multiplication_point')
    def _onchange_s_multiplication_point(self):
        for rec in self:
            if rec.s_rule_type == 'special':
                if rec.s_multiplication_point <= 0:
                    raise ValidationError('Quy tắc đặc biệt %s cần thiết lập giá trị nhân > 0' % rec.name)

    @api.onchange('s_rule_type')
    def _onchange_s_rule_type(self):
        for rec in self:
            if rec.s_rule_type == 'rule_point':
                loyalty_program_id = rec.loyalty_program_id.rule_ids.filtered(lambda l: l.s_rule_type == 'rule_point')
                if len(loyalty_program_id) > 1:
                    raise ValidationError('Không được phép tạo nhiều quy tắc tích điểm trong 1 chương trình khách hàng thân thiết')

    ### viết hàm onchange cho s_rule_date_to và s_rule_date_from với điều kiện s_rule_date_from luôn nhỏ hơn s_rule_date_to
    @api.onchange('s_rule_date_to', 's_rule_date_from')
    def _onchange_s_rule_date_to(self):
        for rec in self:
            if rec.s_rule_date_to and rec.s_rule_date_from:
                if rec.s_rule_date_to < rec.s_rule_date_from:
                    raise ValidationError('Thời gian kết thúc không được nhỏ hơn thời gian bắt đầu')

    # @api.model
    # def create(self, vals_list):
    #     res = super(SAdvancedLoyaltyRule, self).create(vals_list)
    #     if res.s_rule_type == 'special':
    #         if res.s_multiplication_point == 0:
    #             raise ValidationError('Quy tắc đặc biệt %s cần thiết lập giá trị nhân > 0' % res.name)
    #         else:
    #             return res
    #     else:
    #         loyalty_program_ids = res.loyalty_program_id.ids[0]  ###ID loyalty_program bản ghi hiện tại
    #         if loyalty_program_ids:
    #             rule_point_type = self.search([('s_rule_type', '=', 'rule_point')]).filtered(
    #                 lambda l: l.loyalty_program_id.id == loyalty_program_ids)
    #             if len(rule_point_type) > 1:
    #                 raise ValidationError('Không được phép tạo nhiều quy tắc tích điểm trong 1 chương trình khách hàng thân thiết')
    #             else:
    #                 if not res.s_rule_point_id:
    #                     raise ValidationError('Quy tắc tích điểm %s chưa có hạng và tỉ lệ tích điểm' % res.name)
    #                 else:
    #                     for r in res.s_rule_point_id:
    #                         if not r.s_customer_ranked_id:
    #                             raise ValidationError('Quy tắc tích điểm %s chưa thiết lập hạng tích điểm' % res.name)
    #                         elif r.s_proportion_point <= 0:
    #                             raise ValidationError('Quy tắc tích điểm %s chưa thiết lập tỉ lệ tích điểm' % res.name)
    #                     return res
    #         else:
    #             return res
    #
    # def write(self, vals):
    #     res = super(SAdvancedLoyaltyRule, self).write(vals)
    #     for rec in self:
    #         if rec.s_rule_type == 'rule_point':
    #             rule_point = rec.loyalty_program_id.rule_ids.filtered(lambda l: l.s_rule_type == 'rule_point')
    #             if len(rule_point) > 1:
    #                 raise ValidationError('Không được phép tạo nhiều quy tắc tích điểm trong 1 chương trình khách hàng thân thiết')
    #     return res
