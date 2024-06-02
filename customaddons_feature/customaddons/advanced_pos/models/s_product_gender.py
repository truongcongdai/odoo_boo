from odoo import fields, models, api


class SProductGender(models.Model):
    _name = 's.product.gender'
    _description = 'Giới Tính'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
