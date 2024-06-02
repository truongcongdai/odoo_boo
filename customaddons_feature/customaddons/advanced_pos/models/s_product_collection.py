from odoo import fields, models, api


class SProductCollection(models.Model):
    _name = 's.product.collection'
    _description = 'Bộ sưu tập'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
