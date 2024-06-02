from odoo import fields, models, api


class RFMPartnerHistory(models.Model):
    _name = 'rfm.partner.history'
    _description = 'RFM Partner History'
    _rec_name = 'current_segment'

    previous_segment = fields.Many2one(comodel_name='setu.rfm.segment')
    current_segment = fields.Many2one(comodel_name='setu.rfm.segment')
    date_changed = fields.Datetime()
    partner_id = fields.Many2one(comodel_name='res.partner')
    company_id = fields.Many2one(comodel_name='res.company')


class RFMPartnerTeamHistory(models.Model):
    _name = 'rfm.partner.team.history'
    _description = 'RFM Partner Team History'
    _rec_name = 'current_segment'

    previous_segment = fields.Many2one(comodel_name='setu.rfm.segment')
    current_segment = fields.Many2one(comodel_name='setu.rfm.segment')
    date_changed = fields.Datetime()
    partner_id = fields.Many2one(comodel_name='res.partner')
    team_id = fields.Many2one(comodel_name='crm.team')
