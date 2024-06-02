
from odoo import fields, models, api, _


class SLoyaltyProgramInherit(models.Model):
    _inherit = 'loyalty.program'

    points = fields.Float(string="", digits=(12, 6))
