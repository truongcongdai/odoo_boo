import json
import ast
from odoo import fields, models, api


class VaniQueue(models.Model):
    _name = 's.vani.queue'
    _description = 'Vani Queue'

    command = fields.Char(string='API')
    url = fields.Char(
        string='URL',
        required=False)
    data = fields.Text(
        string="DATA",
        required=False)

    def cron_post_vani_points(self):
        queue_ids = self.env['s.vani.queue'].sudo().search([])
        if len(queue_ids) > 0:
            for queue in queue_ids:
                data = ast.literal_eval(queue.data)
                if queue.url == 'points-cancellation':
                    url = self.env['ir.config_parameter'].sudo().get_param('vani.api.url', '') + '/points-cancellation'
                    self.env['base.integrate.vani']._post_data_vani(url, command=queue.command, data=json.dumps(data))
                elif queue.url == 'points-approval':
                    url = self.env['ir.config_parameter'].sudo().get_param('vani.api.url', '') + '/points-approval'
                    self.env['base.integrate.vani']._post_data_vani(url, command=queue.command, data=json.dumps(data))
                queue.unlink()
                self._cr.commit()
