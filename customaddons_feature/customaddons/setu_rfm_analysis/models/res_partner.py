from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError


class ResPartnerRFMSegmentHistory(models.Model):
    _name = 'res.partner.rfm.segment.history'
    _description = """
    Customer RFM segment history table will automatically add records in the table when the customer RFM score will be 
    changed to another one and if the segment value has been changed
    """
    partner_id = fields.Many2one(comodel_name='res.partner', string="Customer")
    history_date = fields.Date(string="History Date")
    old_rfm_segment_id = fields.Many2one(comodel_name="setu.rfm.segment", string="Old RFM Segment", 
                                         help="Customer's Old RFM segment")
    new_rfm_segment_id = fields.Many2one(comodel_name="setu.rfm.segment", string="New RFM Segment", 
                                         help="Customer's New RFM segment")
    old_rfm_score_id = fields.Many2one(comodel_name="setu.rfm.score", string="Old RFM Score", 
                                       help="Customer's Old RFM score")
    new_rfm_score_id = fields.Many2one(comodel_name="setu.rfm.score", string="New RFM Score", 
                                       help="Customer's New RFM score")
    old_segment_rank = fields.Integer(string="Old Segment Rank")
    new_segment_rank = fields.Integer(string="New Segment Rank")
    engagement_direction = fields.Integer(string="Engagement Direction (Up / Down / Consistent)", help="""
        It shows the customer's engagement activities with the business, whether it's increased, decreased or consistent
    """)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    rfm_segment_id = fields.Many2one(comodel_name="setu.rfm.segment", string="RFM Segment", company_dependent=True, 
                                     help="""Connect RFM score with RFM segment""")
    rfm_score_id = fields.Many2one(comodel_name="setu.rfm.score", string="RFM Score", company_dependent=True, 
                                   help="RFM score")

    partner_segment_history_ids = fields.One2many(comodel_name="res.partner.rfm.segment.history", inverse_name="partner_id",
                                                  string="Customer Segment History")
    rfm_team_segment_ids = fields.One2many(comodel_name='partner.segments', inverse_name='partner_id')
    is_dynamic_rule_enable = fields.Boolean(string='Is Dynamic Rule Enable?', compute='check_is_dynamic_rule_enable')

    def check_is_dynamic_rule_enable(self):
        if self.env.user.has_group('setu_rfm_analysis.group_dynamic_rules'):
            self.is_dynamic_rule_enable = True
        else:
            self.is_dynamic_rule_enable = False

    # def write(self, vals):
    #     for partner in self:
    #         current_rfm_segment_id = partner.rfm_segment_id.id
    #         new_rfm_segment_id = vals.get('rfm_segment_id', 0)
    #         if current_rfm_segment_id != new_rfm_segment_id:
    #             self.create_rfm_segment_history()
    #     return super(ResPartner, self).write(vals)

    def create_rfm_segment_history(self, vals):
        rfm_segment_id = self.env['setu.rfm.segment'].search([('id', '=', vals.get('rfm_segment_id', False))])
        new_rank = rfm_segment_id and rfm_segment_id.segment_rank or -1
        old_rank = self.rfm_segment_id.segment_rank
        direction = 0

        if old_rank > new_rank:
            direction = -1
        elif old_rank < new_rank:
            direction = 1
        history_vals = {
            'partner_id': self.id,
            'history_date': date.now(),
            'old_rfm_segment_id': self.rfm_segment_id.id,
            'new_rfm_segment_id': rfm_segment_id or rfm_segment_id.id or False,
            'old_rfm_score_id': self.rfm_score_id.id,
            'new_rfm_score_id': vals.get('rfm_score_id', False),
            'old_segment_rank': old_rank,
            'new_segment_rank': rfm_segment_id and rfm_segment_id.segment_rank or -1,
            'engagement_direction': direction,
        }
        self.env['res.partner.rfm.segment.history'].create(history_vals)

    def open_partner_rfm_segment_history(self):
        action = self.env.ref('setu_rfm_analysis.rfm_partner_history_company_wise_act_window').sudo().read()[0]
        action.update({'domain': [('partner_id', '=', self.id)]})
        return action


class Company(models.Model):
    _inherit = 'res.company'

    take_sales_from_x_days = fields.Integer(string='Sales Of Last X Days', default=365, required=1,
                                            help="For calculation of RFM segment, days inserted here "
                                                 "will be used to fetch past sales data.")
    segment_history_days = fields.Integer(string='Keep Segment History of last X Days', default=365, required=1,
                                          help="RFM Segment History will be kept for days inserted here.")
    segment_configuration_ids = fields.One2many(comodel_name='rfm.segment.configuration', inverse_name='company_id')

    @api.constrains('segment_history_days', 'take_sales_from_x_days')
    def days_constrain(self):
        if self.take_sales_from_x_days > 99999:
            raise UserError('Please enter valid number of days in Sales Of Last X Days field.')
        # if self.segment_history_days > 99999:
        #     raise UserError('Please enter valid number of days in Keep Segment History of last X Days.')

    def open_rfm_segment_rules(self):
        action = self.env.ref('setu_rfm_analysis.rfm_score_configuration_act_window').sudo().read()[0]
        action.update({
            'domain': [('company_id', '=', self.id)],
            'display_name': self.name
        })
        return action


class PartnerSegments(models.Model):
    _name = 'partner.segments'
    _description = 'Partner Segments'

    company_id = fields.Many2one(comodel_name='res.company')
    partner_id = fields.Many2one(comodel_name='res.partner')
    segment_id = fields.Many2one(comodel_name='setu.rfm.segment')
    team_id = fields.Many2one(comodel_name='crm.team')
    score_id = fields.Many2one(comodel_name='setu.rfm.score')
