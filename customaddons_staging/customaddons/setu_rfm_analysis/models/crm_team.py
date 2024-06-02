from odoo import fields, models, api
import json


class SalesTeam(models.Model):
    _inherit = 'crm.team'

    segment_rule_ids = fields.One2many(comodel_name='rfm.segment.team.configuration', inverse_name='team_id')
    dashboard_rfm_graph_data = fields.Text(compute='_compute_rfm_dashboard_graph')
    dashboard_rfm_graph_type = fields.Selection(selection=[
        ('line', 'Line'),
        ('bar', 'Bar'),
    ], string='Type', compute='_compute_rfm_dashboard_graph',
        help='The type of graph this channel will display in the dashboard.')

    def _compute_rfm_dashboard_graph(self):
        for team in self:
            team.dashboard_rfm_graph_type = 'line'
            team.dashboard_rfm_graph_type = 'bar'
            team.dashboard_rfm_graph_data = json.dumps(team._get_rfm_graph())

    def _get_rfm_graph(self):
        team_id = self.id
        list_of_segment_revenue_dict = []
        segments = self.env['setu.rfm.segment'].sudo().search([('crm_team_id', '=', self.id)])
        query_exe = f"""
        SELECT
            seg.name as label,
            sum(data.total_revenue) as value
        FROM
            (
            select
                srs.id,
                coalesce(sum(so.amount_total),0) as total_revenue
            from
                setu_rfm_segment srs
                left join sale_order so on so.rfm_team_segment_id = srs.id
                where srs.crm_team_id = {team_id}
            group by
                srs.id
                
           
            )data inner join setu_rfm_segment seg on data.id = seg.id  
        GROUP BY
            seg.id,seg.name;
        
        """
        pos_q = """ UNION ALL
            
            select
                srs.id,
                coalesce(sum(po.amount_total),0) as total_revenue
            from
                setu_rfm_segment srs
                left join pos_order po on po.rfm_segment_id = srs.id
                where srs.crm_team_id = {team_id}
            group by
                srs.id"""
        self._cr.execute(query_exe)
        data_dict = self._cr.dictfetchall()
        return [
            {
                'values': data_dict,
                'area': True,
                'title': 'Segment Revenue',
                'key': 'Revenue Generated'
                # 'color': '#12F12F'
            }
        ]

    @api.model
    def create(self, vals):
        res = super(SalesTeam, self).create(vals)
        new_created_segment_obj = self.env['setu.rfm.segment']
        for segment in self.env['setu.rfm.segment'].sudo().search([('is_template', '=', True)]):
            new_created_segment_obj |= self.env['setu.rfm.segment'].sudo().create({
                'name': segment.name,
                'is_template': False,
                'crm_team_id': res.id,
                'parent_id': segment.id,
                'seq': segment.seq,
                'segment_rank': segment.segment_rank,
                'segment_description': segment.segment_description,
                'actionable_tips': segment.actionable_tips,
                'team_customer_segment_ids': [(0, 0, {'team_id': res.id})]
            })
            segment.team_customer_segment_ids = [(0, 0, {'team_id': res.id})]
        for segment in new_created_segment_obj:
            self.sudo().with_context(selected_team=res.id).env['rfm.segment.team.configuration'].create({
                'segment_id': segment.id,
                'team_id': res.id
            })
        return res

    def action_open_segments(self):
        segments = self.env['setu.rfm.segment'].sudo().search([('crm_team_id', '=', self.id)])

        return {
            'name': self.name + ' RFM Segments',
            'type': 'ir.actions.act_window',
            'res_model': 'setu.rfm.segment',
            'domain': [('id', 'in', segments.ids)],
            'context': {'create': False, 'current_sales_team_id': self.id},

            'views': [(self.env.ref('setu_rfm_analysis.setu_rfm_segment_kanban_team').id, 'kanban'),
                      (self.env.ref('setu_rfm_analysis.rfm_segment_form').id, 'form')]

        }

    def open_company_wise_teams(self):
        teams = self.sudo().search([('company_id', '=', self.env.user.company_id.id)])
        action = self.env.ref('setu_rfm_analysis.crm_team_rfm_act_window').sudo().read()[0]
        return action
        # return {
        #     'name': 'Sales Teams',
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'crm.team',
        #     # 'domain': [('id', 'in', teams.ids)],
        #     'view_mode': 'kanban',
        #     'view_id': self.env.ref('setu_rfm_analysis.crm_team_rfm_kanban_view').id
        # }
