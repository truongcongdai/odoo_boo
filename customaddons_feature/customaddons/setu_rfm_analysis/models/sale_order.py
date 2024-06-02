from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rfm_segment_id = fields.Many2one(comodel_name="setu.rfm.segment", string="RFM Segment")
    rfm_team_segment_id = fields.Many2one(comodel_name="setu.rfm.segment", string="RFM Sales Team Segment")