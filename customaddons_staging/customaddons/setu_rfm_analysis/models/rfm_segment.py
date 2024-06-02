from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta
from odoo.exceptions import ValidationError, Warning


class SetuRFMSegment(models.Model):
    _name = 'setu.rfm.segment'
    _description = """
        The  idea is to segment customers based on when their last purchase was, 
        how often they’ve purchased in the past, and how much they’ve spent overall. 
        All three of these measures have proven to be effective predictors of a customer's willingness to engage in marketing messages and offers.
    """
    _order = "segment_rank"

    name = fields.Char(string="Name")
    segment_description = fields.Text(string="Activity Description", 
                                      help="""use description to identify who they are.""")
    actionable_tips = fields.Text(string="Actionable Tips", 
                                  help="Suggest recommended marketting action for the segment.")
    rfm_score_ids = fields.One2many(comodel_name="setu.rfm.score", inverse_name="rfm_segment_id", string="RFM Scores")
    rfm_score_syntax = fields.Text(string="RFM Score Syntax")
    rfm_score_condition = fields.Text(string="RFM Score Condition")
    segment_rank = fields.Integer(string="Rank", readonly=True)
    partner_ids = fields.Many2many('res.partner', compute='_compute_res_partner_ids',
                                   help='Partners (Company wise RFM Segment)')

    def _compute_res_partner_ids(self):
        for rec in self:
            if rec.is_template:
                query = f"""
                Select 
                    array_agg(rp.id)
                from res_partner rp
                inner join ir_property ip on 
                    ip.res_id = concat('res.partner,',rp.id::TEXT) and ip.name='rfm_segment_id'
                where ip.company_id = {self.env.company.id} and ip.value_reference = concat('setu.rfm.segment,',
                {rec.id}::text);"""
            else:
                query = f"""
                select 
                    array_agg(partner_id)
                from partner_segments ps
                where segment_id = {rec.id}
                group by segment_id;
                """
            self._cr.execute(query)
            partners = self._cr.fetchall()
            if partners and partners[0] and partners[0][0]:
                rec.partner_ids = self.env['res.partner'].sudo().browse(partners[0][0])
            else:
                rec.partner_ids = False

    order_ids = fields.One2many(comodel_name="sale.order", inverse_name="rfm_segment_id", string="Sale orders")
    team_order_ids = fields.One2many(comodel_name="sale.order", inverse_name="rfm_team_segment_id", 
                                     string="Team Sale orders")
    mailing_ids = fields.One2many(comodel_name="mailing.mailing", inverse_name="rfm_segment_id", string="Mailing")
    total_mailing = fields.Integer(string="Total Mailing", compute='_compute_mailing')

    total_customers = fields.Integer(string="Total Customers", compute='_compute_rfm_common')
    total_orders = fields.Integer(string="Total Orders", compute='_compute_rfm_common')
    total_revenue = fields.Float(string="Total Revenue", compute='_compute_rfm_common')
    team_customer_segment_ids = fields.One2many(comodel_name="team.customer.segment", inverse_name="rfm_segment_id",
                                                string="Team customer segment")

    open_lead_count = fields.Integer(string="Open Leads", compute='_calculate_leads')
    open_rfq_count = fields.Integer(string="Quotations", compute='_calculate_rfq')

    total_customers_ratio = fields.Float(string="Customers", compute='_compute_rfm_common')
    total_orders_ratio = fields.Float(string="Orders", compute='_compute_rfm_common')
    total_revenue_ratio = fields.Float(string="Revenue", compute='_compute_rfm_common')
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    calculated_on = fields.Date(string="Calculated On")
    seq = fields.Integer(default=lambda self: self.get_next_sequence())
    use_dynamic_rules = fields.Boolean(compute='_compute_use_dynamic_rules')
    is_template = fields.Boolean(default=True)
    crm_team_id = fields.Many2one(comodel_name='crm.team', ondelete='cascade')
    parent_id = fields.Many2one(comodel_name='setu.rfm.segment', string='Parent Segment')
    child_ids = fields.One2many(comodel_name='setu.rfm.segment', inverse_name='parent_id', string='Child Segment IDS')
    parent_segment_rank = fields.Integer(related='parent_id.segment_rank', string='Parent Rank')

    def transform_to_dict(self, list_of_dict):
        to_return = {}
        for item in list_of_dict:
            to_return.update({
                item['segment_id']: item
            })
        return to_return

    def _compute_rfm_common(self):
        company_id = self._context.get('allowed_company_ids')[0]
        # company_id = self.env.user.company_id.id
        team = self.mapped('crm_team_id')
        if len(team) == 1:
            team_id = team.id
            company_id = 0
        else:
            team_id = 0
        self._cr.execute(f"select * from compute_rfm_sp({company_id},{team_id},ARRAY{str(self.ids)});")
        rfm_compute_values = self._cr.dictfetchall()
        rfm_compute_values = self.transform_to_dict(rfm_compute_values)
        for segment in self:
            data = rfm_compute_values[segment.id]
            if segment.is_template:
                segment.update({
                    'total_customers': data['partners'],
                    'total_orders': data['company_wise_sales'],
                    'total_revenue': data['company_wise_revenue'],
                    'total_customers_ratio': data['partner_ratio'],
                    'total_orders_ratio': data['sales_ratio'],
                    'total_revenue_ratio': data['revenue_ratio']
                    # 'total_pos_orders': data['company_wise_pos'],
                    # 'total_pos_revenue': data['company_wise_revenue_pos'],
                    # 'total_pos_orders_ratio': data['pos_revenue_ratio'],
                    # 'total_pos_revenue_ratio': data['pos_ratio']
                })
            else:
                segment.update({'total_customers': data['partners'],
                                'total_orders': data['sales_team_wise_sales'],
                                'total_revenue': data['sales_team_wise_revenue'],
                                'total_customers_ratio': data['partner_ratio'],
                                'total_orders_ratio': data['team_sales_ratio'],
                                'total_revenue_ratio': data['team_revenue_ratio'],
                                # 'total_pos_orders': data['sales_team_wise_pos'],
                                # 'total_pos_revenue': data['sales_team_wise_revenue_pos'],
                                # 'total_pos_orders_ratio': data['team_pos_ratio'],
                                # 'total_pos_revenue_ratio': data['team_pos_revenue_ratio']
                                })

    def write(self, vals):
        # if not self.is_template and 'crm_team_id' in vals:
        #     return None
        res = super(SetuRFMSegment, self).write(vals)
        for rec in self:
            if rec.is_template and 'seq' in vals:
                for c in rec.child_ids:
                    c.seq = rec.seq
            if rec.is_template and 'name' in vals:
                for c in rec.child_ids:
                    c.name = rec.name
        return res

    def name_get(self):
        res = [(record.id,
                record.name if record.is_template else record.crm_team_id.name + ' -> ' + record.name if record.crm_team_id else record.name)
               for record in self]
        return res

    def copy(self, default=None):
        raise Warning("Segments can not be Duplicated, please create a new one.")

    def _compute_use_dynamic_rules(self):
        enable_dynamic_rules = self.env.user.has_group('setu_rfm_analysis.group_dynamic_rules')
        for rec in self:
            if enable_dynamic_rules:
                rec.use_dynamic_rules = True
            else:
                rec.use_dynamic_rules = False

    def get_next_sequence(self):
        all_segments = self.search([])
        seq_vals = all_segments.mapped('seq')
        if seq_vals:
            return max(seq_vals) + 1
        return 1

    @api.constrains('seq')
    def seq_constrain(self):
        for rec in self:
            if rec.seq <= 0:
                raise ValidationError('Priority of segment should be greater than zero.')

            if self.is_template:
                duplicate = self.search([('id', '!=', self.id), ('seq', '=', rec.seq), ('is_template', '=', True)])
                if duplicate:
                    raise ValidationError(
                        f"Segment with same priority found. Segment with same priority is [{' ,'.join(duplicate.mapped('name'))}]")

    @api.model
    def create(self, vals):
        res = super(SetuRFMSegment, self).create(vals)
        if res.is_template:
            teams = []
            companies = self.sudo().env['res.company'].search([])
            for company in companies:
                self.sudo().with_context(selected_company=company.id).env['rfm.segment.configuration'].create({
                    'segment_id': res.id,
                    'company_id': company.id
                })
            for team in self.env['crm.team'].sudo().search([]):
                teams.append((0, 0, {'team_id': team.id}))
                s = self.sudo().create({
                    'name': res.name,
                    'is_template': False,
                    'crm_team_id': team.id,
                    'parent_id': res.id,
                    'seq': res.seq,
                    'segment_rank': res.segment_rank,
                    'segment_description': res.segment_description,
                    'actionable_tips': res.actionable_tips,
                    'team_customer_segment_ids': [(0, 0, {'team_id': team.id})]
                })
                self.sudo().with_context(selected_team=team.id).env['rfm.segment.team.configuration'].create({
                    'segment_id': s.id,
                    'team_id': team.id
                })
            res.team_customer_segment_ids = teams
        return res

    def _compute_mailing(self):
        for segment in self:
            segment.total_mailing = len(segment.mailing_ids.ids)

    def _calculate_leads(self):
        won_stage = self.env['crm.stage'].search([('is_won', '=', True)])
        for segment in self:
            if segment.is_template:
                ids = segment.partner_ids and segment.partner_ids.ids or []
            else:
                ids = segment.partner_ids and segment.partner_ids.ids or []
            leads = self.env['crm.lead'].search(
                [('stage_id', 'not in', won_stage.ids), ('partner_id', 'in', ids)])
            segment.open_lead_count = leads and len(leads.ids) or 0

    def _calculate_rfq(self):
        for segment in self:
            if segment.is_template:
                ids = segment.partner_ids and segment.partner_ids.ids or []
            else:
                ids = segment.partner_ids and segment.partner_ids.ids or []
            orders = self.env['sale.order'].search(
                [('state', 'in', ['draft', 'sent']), ('partner_id', 'in', ids)])
            segment.open_rfq_count = orders and len(orders.ids) or 0

    def _compute_customers(self):
        for segment in self:
            segment.update({
                'total_customers': len(segment.partner_ids),
                'total_orders': len(segment.order_ids),
                'total_revenue': sum(segment.mapped('order_ids').mapped('amount_total')),
            })

    def _calculate_ratio(self):
        segments = self.env['setu.rfm.segment'].search([])
        overall_customers = len(segments.mapped('partner_ids').ids)
        overall_orders = len(segments.mapped('order_ids').ids)
        overall_revenue = sum(segments.mapped('order_ids').mapped('amount_total'))

        for segment in self:
            segment.update({
                'total_customers_ratio': overall_customers and round(
                    (segment.total_customers / overall_customers) * 100.0, 2) or 0.01,
                'total_orders_ratio': overall_orders and round((segment.total_orders / overall_orders) * 100.0,
                                                               2) or 0.01,
                'total_revenue_ratio': overall_revenue and round((segment.total_revenue / overall_revenue) * 100.0,
                                                                 2) or 0.01,
            })

    def open_mailing(self):
        kanban_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_kanban').id
        form_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_form').id
        tree_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_tree').id
        graph_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_graph').id
        report_display_views = [(kanban_view_id, 'kanban'), (tree_view_id, 'tree'), (form_view_id, 'form'),
                                (graph_view_id, 'graph')]
        context = self._context.copy() or {}
        context.update({'create': False})
        return {
            'name': _(self.name + ' -> ' + 'Mailings'),
            'domain': [('id', 'in', self.mailing_ids.ids)],
            'res_model': 'mailing.mailing',
            'view_mode': "kanban,tree,form,graph",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
            'context': context
        }

    def open_customer(self):
        kanban_view_id = self.env.ref('base.res_partner_kanban_view').id
        tree_view_id = self.env.ref('base.view_partner_tree').id
        form_view_id = self.env.ref('base.view_partner_form').id
        report_display_views = [(kanban_view_id, 'kanban'), (form_view_id, 'form'), (tree_view_id, 'tree')]
        if self.is_template:
            partners = self.partner_ids.ids
        else:
            partners = self.partner_ids
            # partners = self.env['partner.segments'].search([('segment_id', '=', self.id)]).mapped('partner_id')
            if partners:
                partners = partners.ids
            else:
                partners = []
        context = self._context.copy() or {}
        context.update({'create': False})
        if 'active_id' in context:
            del context['active_id']
        return {
            'name': _(self.name + ' -> ' + 'Customers'),
            'domain': [('id', 'in', partners)],
            'res_model': 'res.partner',
            'context': context,
            'view_mode': "kanban,form,tree",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def open_orders(self):
        form_view_id = self.env.ref('sale.view_order_form').id
        tree_view_id = self.env.ref('sale.view_order_tree').id
        report_display_views = [(tree_view_id, 'tree'), (form_view_id, 'form')]
        if self.is_template:
            ids = self.order_ids.ids
        else:
            ids = self.team_order_ids.ids
        context = self._context.copy() or {}
        context.update({'create': False})
        return {
            'name': _(self.name + ' -> ' + 'Sales Order'),
            'domain': [('id', 'in', ids)],
            'res_model': 'sale.order',
            'context': context,
            'view_mode': "tree,form",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def open_leads(self):
        kanban_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id
        form_view_id = self.env.ref('crm.crm_lead_view_form').id
        tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        report_display_views = [(kanban_view_id, 'kanban'), (tree_view_id, 'tree'), (form_view_id, 'form')]
        won_stage = self.env['crm.stage'].search([('is_won', '=', True)])

        if self.is_template:
            partners = self.partner_ids.ids
        else:
            partners = self.env['partner.segments'].search([('segment_id', '=', self.id)]).mapped('partner_id')
            if partners:
                partners = partners.ids
            else:
                partners = []
        context = self._context.copy() or {}
        context.update({'create': False})
        return {
            'name': _(self.name + ' -> ' + 'Leads'),
            'domain': [('stage_id', 'not in', won_stage.ids), ('partner_id', 'in', partners)],
            'res_model': 'crm.lead',
            'context': context,
            'view_mode': "kanban,tree,form",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def open_rfqs(self):
        form_view_id = self.env.ref('sale.view_order_form').id
        tree_view_id = self.env.ref('sale.view_quotation_tree_with_onboarding').id
        report_display_views = [(tree_view_id, 'tree'), (form_view_id, 'form')]

        if self.is_template:
            partners = self.partner_ids.ids
        else:
            partners = self.env['partner.segments'].search([('segment_id', '=', self.id)]).mapped('partner_id')
            if partners:
                partners = partners.ids
            else:
                partners = []
        context = self._context.copy() or {}
        context.update({'create': False})
        return {
            'name': _(self.name + ' -> ' + 'Quotation'),
            'domain': [('state', 'in', ['draft', 'sent']), ('partner_id', 'in', partners)],
            'res_model': 'sale.order',
            'view_mode': "tree,form",
            'context': context,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def create_mailing(self):
        mailing_env = self.env['mailing.mailing']
        email = self.env.user.partner_id.email or self.env.user.partner_id.company_id and self.env.user.partner_id.company_id.email
        mailing_name = self.name + ' -> ' + self.crm_team_id.name if self.crm_team_id else self.name
        if self.is_template:
            partners = self.partner_ids.ids
        else:
            partners = self.env['partner.segments'].search([('segment_id', '=', self.id)]).mapped('partner_id')
            if partners:
                partners = partners.ids
            else:
                partners = []

        mailing_vals = {
            'name': '%s customers' % mailing_name,
            'mailing_model_id': self.env.ref('base.model_res_partner').id,
            'subject': 'Mailing for %s customers' % self.name,
            'mailing_domain': [("id", "in", partners)],
            'user_id': self.env.user.id,
            'email_from': email,
            'reply_to': email,
            # 'mail_server_id' : mailing_env._get_default_mail_server_id(),
            'medium_id': self.env.ref('utm.utm_medium_email').id,
            'rfm_segment_id': self.id,
            'keep_archives': True
        }
        mailing_env.create(mailing_vals)
        return self.open_mailing()

    def all_open_leads(self):
        kanban_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id
        form_view_id = self.env.ref('crm.crm_lead_view_form').id
        tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        report_display_views = [(tree_view_id, 'tree'), (kanban_view_id, 'kanban'), (form_view_id, 'form')]
        won_stage = self.env['crm.stage'].search([('is_won', '=', True)])
        return {
            'name': 'Open Leads',
            'type': 'ir.actions.act_window',
            'view_mode': "tree,kanban,form",
            'res_model': 'crm.lead',
            'search_view_id': self.env.ref('setu_rfm_analysis.search_rfm_crm_lead').id,
            'context': {'search_default_group_by_rfm_segment_id': 1},
            'views': report_display_views,
            'domain': [('stage_id', 'not in', won_stage.ids), ('partner_id.rfm_segment_id', '!=', False)]
        }

    def all_sale_orders(self):
        form_view_id = self.env.ref('sale.view_order_form').id
        tree_view_id = self.env.ref('sale.view_order_tree').id
        report_display_views = [(tree_view_id, 'tree'), (form_view_id, 'form')]
        return {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'view_mode': "tree,form",
            'search_view_id': self.env.ref('setu_rfm_analysis.search_rfm_quotation').id,
            'res_model': 'sale.order',
            'context': {'search_default_rfm_segment_id': 1},
            'views': report_display_views,
            'domain': [('rfm_segment_id', '!=', False)]
        }

    def all_mailings(self):
        kanban_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_kanban').id
        form_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_form').id
        tree_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_tree').id

        graph_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_graph').id
        report_display_views = [(tree_view_id, 'tree'), (kanban_view_id, 'kanban'), (form_view_id, 'form'),
                                (graph_view_id, 'graph')]
        return {
            'name': 'Mailings',
            'type': 'ir.actions.act_window',
            'view_mode': "tree,kanban,form,graph",
            'res_model': 'mailing.mailing',
            'search_view_id': self.env.ref('setu_rfm_analysis.search_rfm_mailing').id,
            'context': {'search_default_rfm_segment_id': 1},
            'views': report_display_views,
            'domain': [('rfm_segment_id', '!=', False)]
        }

    def update_segment_and_rules(self):
        for segment in self._context.get('active_ids'):
            current_segment = self.browse(segment)
            current_segment.update_child_segments()

    def update_child_segments(self):
        gp_to_append = self.env.user.has_group('setu_rfm_analysis.group_rfm_show_team_conf')
        teams = self.env['crm.team'].sudo().search([])
        associated_teams = self.child_ids.mapped('crm_team_id')
        if associated_teams:
            associated_teams = associated_teams.ids
        else:
            associated_teams = []
        remaining_teams = self.env['crm.team'].sudo().search([('id', 'not in', associated_teams)])
        if remaining_teams:
            for team in remaining_teams:
                self.sudo().create({
                    'name': self.name,
                    'is_template': False,
                    'crm_team_id': team.id,
                    'parent_id': self.id,
                    'seq': self.seq,
                    'team_customer_segment_ids': [(0, 0, {'team_id': team.id})]
                })
        for company in self.env['res.company'].sudo().search([]):
            existing_conf = self.env['rfm.segment.configuration'].sudo().search(
                [('segment_id', '=', self.id), ('company_id', '=', company.id)])
            if existing_conf:
                continue
            else:
                self.sudo().with_context(selected_company=company.id).env['rfm.segment.configuration'].create({
                    'segment_id': self.id,
                    'company_id': company.id
                })

        team_revenue_teams = self.team_customer_segment_ids.mapped('team_id')
        all_teams = teams and teams.ids
        if team_revenue_teams:
            team_revenue_teams = set(team_revenue_teams.ids)
        else:
            team_revenue_teams = set()
        if all_teams:
            all_teams = set(all_teams)
        else:
            all_teams = set()
        remaining_revenue_teams = all_teams.difference(team_revenue_teams)
        remaining_revenue_teams_ids = False
        if remaining_revenue_teams:
            remaining_revenue_teams_ids = list(remaining_revenue_teams)
            remaining_revenue_teams_ids = list(map(lambda id: (0, 0, {'team_id': id}), remaining_revenue_teams_ids))
        if remaining_revenue_teams_ids:
            self.write({
                'team_customer_segment_ids': remaining_revenue_teams_ids
            })
        for child_segment in self.child_ids:
            child_team = child_segment.crm_team_id
            existing_conf = self.env['rfm.segment.team.configuration'].sudo().search(
                [('team_id', '=', child_team.id), ('segment_id', '=', child_segment.id)])
            if existing_conf:
                continue
            else:
                self.sudo().with_context(selected_team=child_team.id).env['rfm.segment.team.configuration'].create({
                    'segment_id': child_segment.id,
                    'team_id': child_team.id
                })

    @api.model
    def update_customer_segment(self):
        # past_x_days_sales = self.env['ir.config_parameter'].sudo().get_param('setu_rfm_analysis.past_x_days_sales')
        date_end = datetime.today()
        # if past_x_days_sales:
        #     date_begin = datetime.today() - relativedelta.relativedelta(days=int(past_x_days_sales))
        # else:
        #     date_begin = datetime.today() - relativedelta.relativedelta(days=365)

        company_ids = self.env['res.company'].sudo().search([])
        calculation_type = 'static'
        if self.env.user.has_group('setu_rfm_analysis.group_dynamic_rules'):
            calculation_type = 'dynamic'
        segment_type = 'company'
        if self.env.user.has_group('setu_rfm_analysis.group_sales_team_rfm'):
            segment_type = 'sales_team'

        query = """
            Select * from update_customer_rfm_segment('%s',null::date,'%s','%s','%s')
        """ % (str(set(company_ids.ids)), date_end, calculation_type, segment_type)
        # print(query)
        self._cr.execute(query)
        for company in company_ids:
            history_date = datetime.today() - relativedelta.relativedelta(days=int(company.segment_history_days))
            history_date = history_date.date()
            history_clean_up_query = f"""delete from rfm_partner_history
                                        where date_changed < '{str(history_date)}' and company_id = {company.id};"""
            self._cr.execute(history_clean_up_query)
