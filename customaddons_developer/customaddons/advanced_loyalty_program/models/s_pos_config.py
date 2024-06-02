from odoo import fields, models, api, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    s_zalo_zns_template_id = fields.Many2one('zns.template', string='ZNS Template')
