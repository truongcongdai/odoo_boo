from odoo import fields, models, api


class SProductSize(models.Model):
    _name = 's.product.size'
    _description = 'Kích cỡ'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
