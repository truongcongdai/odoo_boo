from odoo import fields, models, api


class SProductBrand(models.Model):
    _name = 's.product.brand'
    _description = 'Thương Hiệu'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
