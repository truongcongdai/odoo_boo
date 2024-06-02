from odoo import fields, models, api, _


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    rfm_segment_id = fields.Many2one(comodel_name="setu.rfm.segment", string="RFM Segment",
                                     help="Connect RFM segment with Mailing feature")
