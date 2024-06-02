from odoo import fields, models, api


class SProductColor(models.Model):
    _name = 's.product.color'
    _description = 'Màu Sắc'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
