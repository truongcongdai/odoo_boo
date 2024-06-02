import requests
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    s_select_integration = fields.Selection([('facebook', 'Facebook'), ('zalo', 'Zalo')])

    s_page_id = fields.Char(readonly=True)
    s_access_token_page = fields.Char(readonly=True)

    @api.constrains("s_select_integration")
    def _constrains_select_integration(self):
        search_count_facebook = self.env['helpdesk.team'].search_count([('s_select_integration', '=', 'facebook')])
        search_count_zalo = self.env['helpdesk.team'].search_count([('s_select_integration', '=', 'zalo')])
        if search_count_facebook > 1:
            raise ValidationError('Đã có 1 team tích hợp Facebook')
        if search_count_zalo > 1:
            raise ValidationError('Đã có 1 team tích hợp Zalo')
