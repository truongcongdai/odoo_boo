from odoo import fields, models, api


class SProductSpecies(models.Model):
    _name = 's.product.species'
    _description = 'Chủng loại'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
