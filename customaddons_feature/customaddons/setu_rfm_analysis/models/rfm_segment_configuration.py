from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class RFMSegmentConf(models.Model):
    _name = 'rfm.segment.configuration'
    _description = 'RFM Segment Configuration'

    segment_id = fields.Many2one(comodel_name='setu.rfm.segment', required=True, ondelete='cascade')
    from_amount = fields.Float(required=True, group_operator=False,
                               default=lambda self: self.get_max_value('to_amount')[0])
    to_amount = fields.Float(required=True, group_operator=False,
                             default=lambda self: self.get_max_value('to_amount')[1])
    from_frequency = fields.Integer(required=True, group_operator=False,
                                    default=lambda self: self.get_max_value('to_frequency')[0])
    to_frequency = fields.Integer(required=True, group_operator=False,
                                  default=lambda self: self.get_max_value('to_frequency')[1])
    from_days = fields.Integer(required=True, string='Recency From Past X Days', group_operator=False, default=0)
    to_days = fields.Integer(required=True, string='Recency To Past X Days', group_operator=False, default=lambda self:self.get_to_days())
    company_id = fields.Many2one(comodel_name='res.company', required=True, ondelete='cascade')
    from_atv = fields.Float(required=True, group_operator=False,
                            default=lambda self: self.get_max_value('to_atv')[0])
    to_atv = fields.Float(required=True, group_operator=False,
                          default=lambda self: self.get_max_value('to_atv')[1])

    def copy_rules(self):
        pass

    def get_to_days(self):
        return 365

    def get_max_value(self, field_name):
        company = self.env.context.get('selected_company', False)
        if company:
            rules = self.search([('company_id', '=', company)])
            vals = rules.mapped(field_name)
            max_val = 0
            if vals:
                max_val = max(vals)
            next_val = max_val + 1
            return next_val, next_val + 1
        return 0, 0

    @api.constrains('segment_id', 'from_amount', 'to_amount', 'from_frequency', 'to_frequency', 'from_days', 'to_days',
                    'from_atv', 'to_atv')
    def validation(self):
        errors = ''
        # rules = self.search([('id', '!=', self.id), ('company_id', '=', self.company_id.id)])
        # if rules.filtered(lambda rule: rule.segment_id == self.segment_id):
        #     errors += f'• Rule for {self.segment_id.name} already exists. Multiple rules for same segment is not allowed.\n'
        if self.search([('id', '!=', self.id),
                        ('from_amount', '=', self.from_amount),
                        ('to_amount', '=', self.to_amount),
                        ('from_days', '=', self.from_days),
                        ('to_days', '=', self.to_days),
                        ('from_frequency', '=', self.from_frequency),
                        ('to_frequency', '=', self.to_frequency),
                        ('from_atv', '=', self.from_atv),
                        ('to_atv', '=', self.to_atv),
                        ('company_id', '=', self.company_id.id)
                        ]):
            errors += '• Duplicate rule found for other segment. Please configure rule with different values.\n'

        if self.from_amount > self.to_amount:
            errors += '• From Amount must be less or equal to To Amount.\n'

        if self.to_days <= 0:
            errors += '• To Days must be greater than zero.\n'

        if self.from_frequency > self.to_frequency:
            errors += '• From Frequency must be less or equal to To Frequency.\n'

        if self.from_atv > self.to_atv:
            errors += '• From ATV must be less or equal to To ATV.\n'
        if errors:
            raise ValidationError(_(errors))

        # if rules.filtered(
        #         lambda rule: (rule.from_amount < self.from_amount
        #                       and
        #                       rule.to_amount > self.to_amount)
        #                      or
        #                      (rule.from_amount > self.from_amount
        #                       and
        #                       rule.to_amount < self.to_amount)
        #                      or
        #                      self.from_amount <= rule.from_amount <= self.to_amount <= rule.to_amount
        #                      or
        #                      rule.from_amount <= self.from_amount <= rule.to_amount <= self.to_amount):
        #     errors += "• Rule's Amount range is conflicting with other rules'.\n"
        # if rules.filtered(
        #         lambda rule: (rule.from_frequency < self.from_frequency
        #                       and
        #                       rule.to_frequency > self.to_frequency)
        #                      or
        #                      (rule.from_frequency > self.from_frequency
        #                       and
        #                       rule.to_frequency < self.to_frequency)
        #                      or
        #                      self.from_frequency <= rule.from_frequency <= self.to_frequency <= rule.to_frequency
        #                      or
        #                      rule.from_frequency <= self.from_frequency <= rule.to_frequency <= self.to_frequency):
        #     errors += "• Rule's Frequency range is conflicting with other rules.\n"
        # if rules.filtered(
        #         lambda rule: (rule.from_days < self.from_days
        #                       and
        #                       rule.to_days > self.to_days)
        #                      or
        #                      (rule.from_days > self.from_days
        #                       and
        #                       rule.to_days < self.to_days)
        #                      or
        #                      self.from_days <= rule.from_days <= self.to_days <= rule.to_days
        #                      or
        #                      rule.from_days <= self.from_days <= rule.to_days <= self.to_days):
        #     errors += "• Rule's Days range is conflicting with other rules.\n"


class RFMSegmentTeamConf(models.Model):
    _name = 'rfm.segment.team.configuration'
    _description = 'RFM Segment Team Configuration'

    segment_id = fields.Many2one(comodel_name='setu.rfm.segment', required=True, ondelete='cascade')
    from_amount = fields.Float(required=True, group_operator=False,
                               default=lambda self: self.get_max_value('to_amount')[0])
    to_amount = fields.Float(required=True, group_operator=False,
                             default=lambda self: self.get_max_value('to_amount')[1])
    from_frequency = fields.Integer(required=True, group_operator=False,
                                    default=lambda self: self.get_max_value('to_frequency')[0])
    to_frequency = fields.Integer(required=True, group_operator=False,
                                  default=lambda self: self.get_max_value('to_frequency')[1])
    from_days = fields.Integer(required=True, string='Recency From Past X Days', group_operator=False, default=0)
    to_days = fields.Integer(required=True, string='Recency To Past X Days', group_operator=False,
                             default=lambda self: self.get_to_days())
    team_id = fields.Many2one(comodel_name='crm.team', required=True, ondelete='cascade')
    from_atv = fields.Float(required=True, group_operator=False,
                            default=lambda self: self.get_max_value('to_atv')[0])
    to_atv = fields.Float(required=True, group_operator=False,
                          default=lambda self: self.get_max_value('to_atv')[1])

    def get_to_days(self):
        return 365

    def get_max_value(self, field_name):
        team = self.env.context.get('selected_team', False)
        if team:
            rules = self.search([('team_id', '=', team)])
            vals = rules.mapped(field_name)
            max_val = 0
            if vals:
                max_val = max(vals)
            next_val = max_val + 1
            return next_val, next_val + 1
        return 0, 0

    @api.constrains('segment_id', 'from_amount', 'to_amount', 'from_frequency', 'to_frequency', 'from_days', 'to_days',
                    'from_atv', 'to_atv')
    def validation(self):
        errors = ''
        # rules = self.search([('id', '!=', self.id), ('company_id', '=', self.company_id.id)])
        # if rules.filtered(lambda rule: rule.segment_id == self.segment_id):
        #     errors += f'• Rule for {self.segment_id.name} already exists. Multiple rules for same segment is not allowed.\n'
        if self.search([('id', '!=', self.id),
                        ('from_amount', '=', self.from_amount),
                        ('to_amount', '=', self.to_amount),
                        ('from_days', '=', self.from_days),
                        ('to_days', '=', self.to_days),
                        ('from_frequency', '=', self.from_frequency),
                        ('to_frequency', '=', self.to_frequency),
                        ('from_atv', '=', self.from_atv),
                        ('to_atv', '=', self.to_atv),
                        ('team_id', '=', self.team_id.id)
                        ]):
            errors += '• Duplicate rule found for other segment. Please configure rule with different values.\n'

        if self.from_amount > self.to_amount:
            errors += '• From Amount must be less or equal to To Amount.\n'

        if self.to_days <= 0:
            errors += '• To Days must be greater than zero.\n'

        if self.from_frequency > self.to_frequency:
            errors += '• From Frequency must be less or equal to To Frequency.\n'

        if self.from_atv > self.to_atv:
            errors += '• From ATV must be less or equal to To ATV.\n'


        # if rules.filtered(
        #         lambda rule: (rule.from_amount < self.from_amount
        #                       and
        #                       rule.to_amount > self.to_amount)
        #                      or
        #                      (rule.from_amount > self.from_amount
        #                       and
        #                       rule.to_amount < self.to_amount)
        #                      or
        #                      self.from_amount <= rule.from_amount <= self.to_amount <= rule.to_amount
        #                      or
        #                      rule.from_amount <= self.from_amount <= rule.to_amount <= self.to_amount):
        #     errors += "• Rule's Amount range is conflicting with other rules'.\n"
        # if rules.filtered(
        #         lambda rule: (rule.from_frequency < self.from_frequency
        #                       and
        #                       rule.to_frequency > self.to_frequency)
        #                      or
        #                      (rule.from_frequency > self.from_frequency
        #                       and
        #                       rule.to_frequency < self.to_frequency)
        #                      or
        #                      self.from_frequency <= rule.from_frequency <= self.to_frequency <= rule.to_frequency
        #                      or
        #                      rule.from_frequency <= self.from_frequency <= rule.to_frequency <= self.to_frequency):
        #     errors += "• Rule's Frequency range is conflicting with other rules.\n"
        # if rules.filtered(
        #         lambda rule: (rule.from_days < self.from_days
        #                       and
        #                       rule.to_days > self.to_days)
        #                      or
        #                      (rule.from_days > self.from_days
        #                       and
        #                       rule.to_days < self.to_days)
        #                      or
        #                      self.from_days <= rule.from_days <= self.to_days <= rule.to_days
        #                      or
        #                      rule.from_days <= self.from_days <= rule.to_days <= self.to_days):
        #     errors += "• Rule's Days range is conflicting with other rules.\n"
        if errors:
            raise ValidationError(_(errors))
