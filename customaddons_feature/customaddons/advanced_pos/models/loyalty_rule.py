
from odoo import fields, models, api, _


class SLoyaltyRuleInherit(models.Model):
    _inherit = 'loyalty.rule'

    points_currency = fields.Float(string="", digits=(12, 6))
