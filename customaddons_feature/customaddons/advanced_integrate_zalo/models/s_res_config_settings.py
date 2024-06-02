from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import requests
import urllib3
import datetime as date
from datetime import datetime
import traceback
import logging

_logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    s_zalo_app_id = fields.Char("App ID", config_parameter="advanced_integrate_zalo.app_id")
    s_zalo_app_secret = fields.Char("App secret", config_parameter="advanced_integrate_zalo.app_secret")
    s_is_connected_zalo = fields.Boolean("Is connected  Lazada",
                                         config_parameter="advanced_integrate_zalo.is_connected_zalo")
    s_url_endpoint = fields.Char("App secret", config_parameter="advanced_integrate_zalo.s_url_endpoint")
    s_url_endpoint_oa = fields.Char("URL OA", config_parameter="advanced_integrate_zalo.s_url_endpoint_oa")
    s_url_oauth = fields.Char("App secret", config_parameter="advanced_integrate_zalo.s_url_oauth")
    s_zalo_url_image = fields.Char("Url Image", config_parameter="advanced_integrate_zalo.s_zalo_url_image", default="False")
    zalo_mode = fields.Selection([("sandbox", "Sandbox"), ("product", "Product")], requried=True, default="sandbox",
                                 config_parameter="advanced_integrate_zalo.zalo_mode")

    @api.onchange('zalo_mode')
    def _onchange_zalo_mode(self):
        ir_config_param_obj = self.env['ir.config_parameter'].sudo()
        if self.zalo_mode:
            ir_config_param_obj.set_param('advanced_integrate_zalo.zalo_mode', self.zalo_mode)

    def btn_connect_zalo(self):
        if self.s_zalo_app_id:
            url = self.s_url_oauth + "/oa/permission?app_id=" + self.s_zalo_app_id + "&redirect_uri=" + self.env[
                'ir.config_parameter'].sudo().get_param('web.base.url') + '/authorization_oa_zalo'
            return {
                'name': 'Authorization',
                'type': 'ir.actions.act_url',
                'url': url,  # Replace this with tracking link
                'target': 'new',  # you can change target to current, self, new.. etc
            }
        else:
            raise ValidationError("Invalid Client ID")

    def btn_disconnect_zalo(self):
        ir_config_param_obj = self.env['ir.config_parameter'].sudo()
        ir_config_param_obj.set_param('advanced_integrate_zalo.is_connected_zalo', False)
        ir_config_param_obj.search([('key', '=', 'advanced_integrate_zalo.access_token')]).unlink()
        ir_config_param_obj.search([('key', '=', 'advanced_integrate_zalo.refresh_token')]).unlink()
        ir_config_param_obj.search([('key', '=', 'advanced_integrate_zalo.expires_in')]).unlink()
        ir_config_param_obj.search([('key', '=', 'advanced_integrate_zalo.is_connected_zalo')]).unlink()

    def refresh_token_zalo(self):
        ir_config_param_obj = self.env['ir.config_parameter'].sudo()
        url = ir_config_param_obj.get_param('advanced_integrate_zalo.s_url_oauth') + '/oa/access_token'
        params = {'app_id': ir_config_param_obj.get_param('advanced_integrate_zalo.app_id'),
                  'grant_type': 'refresh_token',
                  'refresh_token': ir_config_param_obj.get_param('advanced_integrate_zalo.refresh_token')
                  }
        headers = {'secret_key': ir_config_param_obj.get_param('advanced_integrate_zalo.app_secret')}
        res = requests.post(url,
                            data={},
                            params=params,
                            headers=headers,
                            verify=False
                            )
        if res.status_code == 200:
            res_data = res.json()
            try:
                ir_config_param_obj.set_param('advanced_integrate_zalo.access_token', res_data['access_token'])
                ir_config_param_obj.set_param('advanced_integrate_zalo.refresh_token', res_data['refresh_token'])
                ir_config_param_obj.set_param('advanced_integrate_zalo.expires_in', res_data['expires_in'])
                ir_config_param_obj.set_param('advanced_integrate_zalo.is_connected_zalo', True)
                self.env['ir.logging'].sudo().create({
                    'type': 'server',
                    'name': 'Refresh Token',
                    'path': 'url',
                    'line': 0,
                    'func': 'func',
                    'message': "nextcall: %s lastcall: %s" % (self.env.ref('advanced_integrate_zalo.ir_cron_refresh_update_token').nextcall, self.env.ref('advanced_integrate_zalo.ir_cron_refresh_update_token').lastcall)
                })
            except Exception as e:
                _logger.error(traceback.format_exc())
                self.env['ir.logging'].sudo().create({
                    'type': 'server',
                    'name': 'Refresh Token',
                    'path': 'url',
                    'line': 0,
                    'func': 'func',
                    'message': str(res_data.get('error_description'))
                })
        else:
            raise ValidationError("Refresh Token Failed")
