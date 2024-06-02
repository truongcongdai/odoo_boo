from odoo import fields, models, api


class SProductMaterial(models.Model):
    _name = 's.product.material'
    _description = 'Chất liệu'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
