from odoo import fields, models, api


class SlostBillPosOrderLineInherit(models.Model):
    _inherit = 's.lost.bill.pos.order.line'

    loyalty_points = fields.Float('Loyalty Points')
