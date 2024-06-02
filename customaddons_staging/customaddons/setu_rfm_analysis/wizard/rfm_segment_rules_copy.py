from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class RFMGlobalConfLine(models.TransientModel):
    _name = 'rfm.global.conf.line'
    _description = 'RFM Global Conf. Line'

    global_id = fields.Many2one(comodel_name='rfm.global.conf')
    segment_id = fields.Many2one(comodel_name='setu.rfm.segment')
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
    from_atv = fields.Float(required=True, group_operator=False,
                            default=lambda self: self.get_max_value('to_atv')[0])
    to_atv = fields.Float(required=True, group_operator=False,
                          default=lambda self: self.get_max_value('to_atv')[1])

    def get_max_value(self, field_name):
        rules = self.search([])
        vals = rules.mapped(field_name)
        max_val = 0
        if vals:
            max_val = max(vals)
        next_val = max_val + 1
        return next_val, next_val + 1

    def get_to_days(self):
        return 365

    @api.constrains('segment_id', 'from_amount', 'to_amount', 'from_frequency', 'to_frequency', 'from_days', 'to_days',
                    'from_atv', 'to_atv')
    def validation(self):
        errors = ''
        if self.search([('id', '!=', self.id),
                        ('from_amount', '=', self.from_amount),
                        ('to_amount', '=', self.to_amount),
                        ('from_days', '=', self.from_days),
                        ('to_days', '=', self.to_days),
                        ('from_frequency', '=', self.from_frequency),
                        ('to_frequency', '=', self.to_frequency),
                        ('from_atv', '=', self.from_atv),
                        ('to_atv', '=', self.to_atv),
                        ('global_id', '=', self.global_id.id)
                        ]):
            self.search([('global_id', '=', self.global_id.id)])
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


class RFMGlobalConf(models.TransientModel):
    _name = 'rfm.global.conf'
    _description = 'RFM Global Conf.'

    global_for_company = fields.Boolean(default=True)
    global_for_sales_team = fields.Boolean(default=True)
    global_rule_lines = fields.One2many(comodel_name='rfm.global.conf.line', inverse_name='global_id')

    @api.model
    def create(self, vals):
        res = super(RFMGlobalConf, self).create(vals)
        segment_templates = self.env['setu.rfm.segment'].sudo().search([('is_template', '=', True)])
        for segment in segment_templates:
            self.env['rfm.global.conf.line'].create({
                'global_id': res.id,
                'segment_id': segment.id
            })
        return res

    def create_open_global_conf_wizard(self):
        self.env['rfm.global.conf.line'].sudo().search([]).unlink()
        res = self.create({})
        action = self.env['ir.actions.act_window']._for_xml_id('setu_rfm_analysis.global_segment_rules_act_window')
        action['res_id'] = res.id
        return action

    def make_global_rule(self):
        if self.global_for_company:
            companies = self.env['res.company'].sudo().search([])
            for c in companies:
                c_rules = self.env['rfm.segment.configuration'].search([('company_id', '=', c.id)])
                for from_rule in self.global_rule_lines:
                    to_rule = c_rules.filtered(lambda r: r.segment_id == from_rule.segment_id)
                    to_rule.write({
                        'from_days': from_rule.from_days,
                        'from_frequency': from_rule.from_frequency,
                        'from_amount': from_rule.from_amount,
                        'from_atv': from_rule.from_atv,
                        'to_days': from_rule.to_days,
                        'to_frequency': from_rule.to_frequency,
                        'to_amount': from_rule.to_amount,
                        'to_atv': from_rule.to_atv
                    })
        if self.global_for_sales_team:
            teams = self.env['crm.team'].sudo().search([])
            for t in teams:
                t_rules = self.env['rfm.segment.team.configuration'].search([('team_id', '=', t.id)])
                for from_rule in self.global_rule_lines:
                    to_rule = t_rules.filtered(lambda r: r.segment_id.parent_id == from_rule.segment_id)
                    to_rule.write({
                        'from_days': from_rule.from_days,
                        'from_frequency': from_rule.from_frequency,
                        'from_amount': from_rule.from_amount,
                        'from_atv': from_rule.from_atv,
                        'to_days': from_rule.to_days,
                        'to_frequency': from_rule.to_frequency,
                        'to_amount': from_rule.to_amount,
                        'to_atv': from_rule.to_atv
                    })


class RFMRuleCopy(models.TransientModel):
    _name = 'copy.rule.conf'
    _description = 'Copy Rule Configuration'

    copy_rules_from = fields.Selection(lambda self: self.get_selection_values(), string='Copy Rules From',
                                       default='Company')
    rule_company_id = fields.Many2one(comodel_name='res.company')
    rule_team_id = fields.Many2one(comodel_name='crm.team')

    copy_rules_to = fields.Selection(lambda self: self.get_selection_values(), string='Copy Rules To',
                                     default='Company')
    to_rule_company_id = fields.Many2one(comodel_name='res.company')
    to_rule_team_id = fields.Many2one(comodel_name='crm.team')

    def get_selection_values(self):
        pass
        if self.env.user.has_group('setu_rfm_analysis.group_sales_team_rfm'):
            return [('Company', 'Company'), ('Sales Team', 'Sales Team')]
        else:
            return [('Company', 'Company')]

    def copy_rules(self):
        if self.copy_rules_from == 'Company':
            from_rules = self.env['rfm.segment.configuration'].search([('company_id', '=', self.rule_company_id.id)])
        else:
            from_rules = self.env['rfm.segment.team.configuration'].search([('team_id', '=', self.rule_team_id.id)])

        if self.copy_rules_to == 'Company':
            to_rules = self.env['rfm.segment.configuration'].search([('company_id', '=', self.to_rule_company_id.id)])
        else:
            to_rules = self.env['rfm.segment.team.configuration'].search([('team_id', '=', self.to_rule_team_id.id)])

        for from_rule in from_rules:
            to_rule = to_rules.filtered(lambda r: (r.segment_id.parent_id or r.segment_id) == (
                    from_rule.segment_id.parent_id or from_rule.segment_id))
            to_rule.write({
                'from_days': from_rule.from_days,
                'from_frequency': from_rule.from_frequency,
                'from_amount': from_rule.from_amount,
                'from_atv': from_rule.from_atv,
                'to_days': from_rule.to_days,
                'to_frequency': from_rule.to_frequency,
                'to_amount': from_rule.to_amount,
                'to_atv': from_rule.to_atv
            })
