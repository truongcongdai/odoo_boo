from odoo import fields, models, api


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    rfm_segment_id = fields.Many2one(comodel_name='setu.rfm.segment', compute='_compute_rfm_segment', store=True)

    @api.depends('partner_id', 'partner_id.rfm_segment_id')
    def _compute_rfm_segment(self):
        for lead in self:
            if lead.partner_id.rfm_segment_id:
                lead.rfm_segment_id = lead.partner_id.rfm_segment_id
            else:
                lead.rfm_segment_id = False
