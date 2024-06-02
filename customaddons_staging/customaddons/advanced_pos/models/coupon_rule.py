
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SCouponRuleInherit(models.Model):
    _inherit = 'coupon.rule'
    _description = "Coupon Rule"

    s_apply_rule_maximum = fields.Boolean(string='Đơn hàng có giá trị đến')
    s_rule_maximum_amount = fields.Float(default=0.0, help="Maximum required amount to get the reward")
    s_rule_maximum_amount_tax_inclusion = fields.Selection([
        ('tax_included', 'Tax Included'),
        ('tax_excluded', 'Tax Excluded')], default="tax_excluded")

    @api.constrains('s_rule_maximum_amount', 'rule_minimum_amount')
    def _check_s_apply_rule_maximum(self):
        if self.s_apply_rule_maximum:
            if self.s_rule_maximum_amount < 0:
                raise ValidationError(_('Maximum purchased amount should be greater than 0'))
            if self.s_rule_maximum_amount < self.rule_minimum_amount:
                raise ValidationError(_('Maximum purchased amount should be greater than Minimum purchased amount'))
