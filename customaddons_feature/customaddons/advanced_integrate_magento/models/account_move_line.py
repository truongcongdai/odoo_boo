from odoo import fields, models, api


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    m2_total_line_discount = fields.Float(string='Chiết khấu M2')
