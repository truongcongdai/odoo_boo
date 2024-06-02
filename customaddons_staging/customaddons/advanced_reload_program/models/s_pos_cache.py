from odoo import fields, models, api
from ast import literal_eval


class SPosCache(models.Model):
    _name = 's.pos.cache'
    _description = 'Super POS Cache'

    # program_domain = fields.Text(required=True)
    program_fields = fields.Text(required=True)
    config_id = fields.Many2one('pos.config', ondelete='cascade', required=True)

    def get_program_cache(self, config_id):
        program_cache = self.env['s.pos.cache'].sudo().search([('config_id', '=', config_id)], limit=1)
        if program_cache.program_fields:
            return program_cache.program_fields
        return []
