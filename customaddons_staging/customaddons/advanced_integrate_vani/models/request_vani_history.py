from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RequestVaniHistory(models.Model):
    _name = 'request.vani.history'

    request_id = fields.Char(string="RequestId Vani")
    vani_url = fields.Char(string="Vani URL")
    param = fields.Text(string="Param Body")

    def check_points_filling_info(self):
        message = self.env['res.partner'].get_points_filling_info(request_id=self.request_id)
        raise ValidationError(message.text)
