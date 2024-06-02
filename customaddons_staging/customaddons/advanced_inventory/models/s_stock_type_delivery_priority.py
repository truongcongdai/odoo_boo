from odoo import fields, models, api
from odoo.exceptions import ValidationError


class SStockTypeDeliverySequence(models.Model):
    _name = 's.stock.type.delivery.priority'
    _description = 'Mức độ ưu tiên'

    name = fields.Char(string='Tên', required=True)
    thoi_gian_thuc_hien = fields.Integer(string='Thời gian thực hiện', required=True)

    @api.constrains('thoi_gian_thuc_hien')
    def check_thoi_gian_thuc_hien(self):
        for rec in self:
            if rec.thoi_gian_thuc_hien > 100000:
                raise ValidationError('Thời gian thực hiện phải nhỏ hơn 100.000.')
