from odoo import models, api, fields, _
import requests
from odoo.http import request
from datetime import date, timedelta
# from ..models.res_config_settings import connect_bravo
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class BaseIntegrateBravo(models.Model):
    _name = 'base.integrate.bravo'

    def connect_bravo(self):
        self.env['ir.config_parameter'].sudo().set_param('bravo.bravo_is_connected', True)
        try:
            bravo_url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '')
            bravo_username = self.env['ir.config_parameter'].sudo().get_param('bravo.username', '')
            bravo_password = self.env['ir.config_parameter'].sudo().get_param('bravo.password', '')
            data = dict(
                username=bravo_username,
                password=bravo_password,
                grant_type='password'
            )
            res = requests.get(
                url=bravo_url + '/token',
                data=data
            )
            if res.status_code == 200:
                access_token_bravo = res.json().get('access_token', '')
                expires_days_bravo = res.json().get('expires_in', 0)
                self.env['ir.config_parameter'].sudo().set_param('bravo.token', access_token_bravo)
                self.env['ir.config_parameter'].sudo().set_param('bravo.bravo_connected_date', date.today())
                self.env['ir.config_parameter'].sudo().set_param('bravo.bravo_expires_days', expires_days_bravo)
                return res
        except Exception as e:
            _logger.error('Can not connect Bravo from params')
            raise ValidationError(e.args)

    def get_bravo_parammeter_data(self):
        bravo_url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '')
        bravo_username = self.env['ir.config_parameter'].sudo().get_param('bravo.username', '')
        bravo_password = self.env['ir.config_parameter'].sudo().get_param('bravo.password', '')
        bravo_token = self.env['ir.config_parameter'].sudo().get_param('bravo.token', '')
        bravo_connected_date = self.env['ir.config_parameter'].sudo().get_param('bravo.bravo_connected_date', '')
        bravo_expires_days = self.env['ir.config_parameter'].sudo().get_param('bravo.bravo_expires_days', '')
        bravo_parammeter_data = {
            'bravo_url': bravo_url,
            'bravo_username': bravo_username,
            'bravo_password': bravo_password,
            'bravo_token': bravo_token,
            'bravo_connected_date': bravo_connected_date,
            'bravo_expires_days': bravo_expires_days
        }
        return bravo_parammeter_data

    def cron_get_token_bravo(self):
        # bravo_data = self.get_bravo_parammeter_data()
        # connected_date_token_bravo = bravo_data.get('bravo_connected_date'),
        # expires_days_token_bravo = bravo_data.get('bravo_expires_days'),
        # expires_date_last = date.fromisoformat(connected_date_token_bravo[0]) + timedelta(days=int(expires_days_token_bravo[0]))
        # expires_days_total = expires_date_last - date.today()
        # if int(expires_days_total.days) == 1:
        self.sudo().get_token_bravo()

    def get_token_bravo(self):
        res = self.connect_bravo()
        if res and res.status_code == 200:
            access_token_bravo = res.json().get('access_token', '')
            # self.env['ir.config_parameter'].sudo().set_param('bravo.token', access_token_bravo)
            return access_token_bravo

    def _post_data_bravo(self, url,token, command, data=None, files=None, params={}, headers=None):
        # bravo_data = self.get_bravo_parammeter_data()
        if headers == None:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer %s' % (token,),
            }
        try:
            # user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '')
            headers.update({'User-Agent': 'Odoo'})
        except Exception as e:
            _logger.debug("USER_AGENT Error: %r", e)
        data = data or dict()
        res = requests.post(
            url,
            data=data,
            params=params,
            files=files,
            headers=headers,
            verify=False
        )
        resp = res.json()
        if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': res.text + str(data),
                'path': url,
                'func': '_post_data_bravo',
                'line': '0',
            })
            error_bravo_config = self.env.ref('advanced_integrate_bravo.post_sync_error_bravo_config_parameter')
            if error_bravo_config and error_bravo_config.value == 'False':
                error_bravo_config.sudo().value = 'True'
        else:
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'message': res.text + str(data),
                'path': url,
                'func': '_post_data_bravo',
                'line': '0',
            })
        return res
