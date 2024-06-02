from odoo import api, SUPERUSER_ID


def create_segments(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    parent_segments = env['setu.rfm.segment'].sudo().search([('is_template', '=', True)])
    companies = env['res.company'].sudo().search([])
    for parent_segment in parent_segments:
        for company in companies:
            env['rfm.segment.configuration'].sudo().with_context(selected_company=company.id).create({
                'segment_id': parent_segment.id,
                'company_id': company.id
            })
        for team in env['crm.team'].sudo().search([]):
            env['setu.rfm.segment'].sudo().create({
                'name': parent_segment.name,
                'is_template': False,
                'crm_team_id': team.id,
                'parent_id': parent_segment.id,
                'seq': parent_segment.seq,
                'team_customer_segment_ids': [(0, 0, {'team_id': team.id})]
            })
