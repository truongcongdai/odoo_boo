from odoo import fields, models
from odoo.exceptions import ValidationError
import requests
import json


class BaseIntegrateZalo(models.Model):
    _name = "base.integrate.zalo"

    def get_data_zalo_zns(self, api, data=None, params=None):
        ir_config_param_obj = self.env['ir.config_parameter'].sudo()

        url = ir_config_param_obj.get_param("advanced_integrate_zalo.s_url_endpoint") + api
        if ir_config_param_obj.get_param("advanced_integrate_zalo.access_token"):
            headers = {"access_token": ir_config_param_obj.get_param("advanced_integrate_zalo.access_token")}
            response = requests.get(
                url,
                data=data,
                params=params,
                headers=headers,
                verify=False
            )
            data = response.json()
            if response.status_code == 200:
                if data['error'] == 0:
                    return data
                else:
                    raise ValidationError(data['message'])
        else:
            raise ValidationError("Access Token is not found")

    def post_data_zalo_zns(self, api, data=None, params=None):
        ir_config_param_obj = self.env['ir.config_parameter'].sudo()
        url = ir_config_param_obj.get_param("advanced_integrate_zalo.s_url_endpoint") + api
        payload = json.dumps(data)
        token = ir_config_param_obj.get_param("advanced_integrate_zalo.access_token")
        if token:
            headers = {"access_token": token}
            response = requests.post(
                url,
                data=payload,
                params=params,
                headers=headers,
                verify=False
            )
            data = response.json()
            if response.status_code == 200:
                return data
        else:
            raise ValidationError("Access Token not found")

