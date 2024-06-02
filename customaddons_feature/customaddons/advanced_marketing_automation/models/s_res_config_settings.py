from odoo import fields, models, api,_
from odoo.exceptions import ValidationError
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def get_template_zns(self):
        api = '/template/all'
        params = {'offset': 0, 'limit': 100}
        response = self.env['base.integrate.zalo'].get_data_zalo_zns(api, data=None, params=params)
        if response:
            if response['error'] == 0:
                return response['data']

    def sync_template_zns(self):
        template_ids = self.get_template_zns()
        if template_ids:
            for template_id in template_ids:
                if template_id['status'] == "ENABLE" and template_id['templateId'] not in self.env[
                    'zns.template'].search([]).mapped(
                    's_template_id'):
                    self.env['zns.template'].create({
                        'name': template_id['templateName'],
                        's_template_id': template_id['templateId']
                    })
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Đồng bộ ZNS'),
                    'message': 'Đồng bộ thành công ',
                    'sticky': False,
                }
            }
            return notification

