from datetime import date
import urllib.parse
import requests

from odoo import fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    s_client_id = fields.Char(string="Client Id", config_parameter='advanced_helpdesk.facebook_client_id')
    s_client_secret = fields.Char(string="Client Secret", config_parameter='advanced_helpdesk.facebook_client_secret')
    s_url_facebook = fields.Char(string="Url Facebook", config_parameter='advanced_helpdesk.url_facebook')
    s_access_token_facebook = fields.Char(string="Access Token",
                                          config_parameter='advanced_helpdesk.facebook_access_token')
    s_facebook_page_id = fields.Char(string="Id Page",
                                          config_parameter='advanced_helpdesk.facebook_page_id')
    s_token_page_facebook = fields.Char(string="Access Token Page",
                                        config_parameter='advanced_helpdesk.facebook_access_token_page')
    s_facebook_connected_date = fields.Char(string="Facebook connected Date",
                                            config_parameter='advanced_helpdesk.facebook_connect_date')
    s_is_connect_facebook = fields.Boolean(config_parameter='advanced_helpdesk.facebook_is_connect')


    def btn_connect_facebook(self):
        if self.s_client_id:
            redirect_url = "%s/facebook/callback/" % self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = urllib.parse.quote(redirect_url, safe="")
            url = "https://facebook.com/v6.0/dialog/oauth?client_id=%s&redirect_uri=%s&state=987654321" % (
                self.s_client_id, redirect_uri)
            return {
                'name': 'AuthorizationFacebook',
                'type': 'ir.actions.act_url',
                'url': url,  # Replace this with tracking link
                'target': 'new',  # you can change target to current, self, new.. etc
            }
        else:
            raise ValidationError("Invalid Client ID")

    def btn_disconnect_facebook(self):
        self.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_is_connect', False)
        self.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_access_token', '')
        self.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_access_token_page', '')
        self.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_auth.key', '')

    def get_token_page_facebook(self):
        try:
            page_id = self.env['ir.config_parameter'].sudo().get_param('advanced_helpdesk.facebook_page_id')
            url = "{url_facebook}/me/accounts".format(
                url_facebook=self.env['ir.config_parameter'].sudo().get_param('advanced_helpdesk.url_facebook'))
            params = dict(
                access_token=self.env['ir.config_parameter'].sudo().get_param('advanced_helpdesk.facebook_access_token')
            )
            res = requests.get(
                url=url,
                params=params,
                verify=False
            )
            if res.status_code == 200:
                for rec in res.json()['data']:
                    if 'access_token' in rec and rec.get('id') == page_id:
                        self.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_access_token_page',
                                                                         rec['access_token'])
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Get-Token-Page-Facebook',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'get_token_page_facebook',
                'line': '0',
            })


    def _get_refresh_token_facebook(self):
        try:
            client_id = self.env['ir.config_parameter'].sudo().get_param('advanced_helpdesk.facebook_client_id', '')
            client_secret = self.env['ir.config_parameter'].sudo().get_param(
                'advanced_helpdesk.facebook_client_secret')
            url = "{url_facebook}/oauth/access_token".format(
                url_facebook=self.env['ir.config_parameter'].sudo().get_param(
                    'advanced_helpdesk.url_facebook'))
            params = dict(
                grant_type='fb_exchange_token',
                client_id=client_id,
                client_secret=client_secret,
                fb_exchange_token=self.env['ir.config_parameter'].sudo().get_param('advanced_helpdesk.facebook_access_token'),
                auth_type="rerequest",
                scope="pages_messaging,pages_show_list,public_profile,pages_read_engagement,pages_manage_metadata"
            )
            res = requests.get(
                url=url,
                params=params,
                verify=False
            )
            if res.status_code == 200:
                access_token_facebook = res.json().get('access_token', '')
                self.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_access_token',access_token_facebook)
                self.sudo().get_token_page_facebook()
                # self.get_token_page_facebook()
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': '_get_refresh_token_facebook',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': '_get_refresh_token_facebook',
                'line': '0',
            })

