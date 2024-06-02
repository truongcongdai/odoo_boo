from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class IrCron(models.Model):
    _name = 'ir.cron'
    _inherit = 'ir.cron'

    table_ids = fields.One2many('izi.table', 'cron_id', string='Tables')
    analytic = fields.Boolean('For Analytic Purpose')

class ServerAction(models.Model):
    _inherit = 'ir.actions.server'

    def _get_eval_context(self, action=None):
        eval_context = super(ServerAction, self)._get_eval_context(action=action)
        if self.usage == 'ir_cron':
            cron = self.env['ir.cron'].search(['|', ('active', '=', True), ('active', '=', False), ('ir_actions_server_id', '=', self.id)], limit=1)
            eval_context['cron'] = cron
        if self._context.get('izi_table'):
            eval_context['izi_table'] = self._context.get('izi_table')
        eval_context['self'] = self
        eval_context['izi'] = self.env['izi.tools']
        return eval_context