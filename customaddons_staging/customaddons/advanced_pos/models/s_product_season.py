from odoo import fields, models, api


class SProductSeason(models.Model):
    _name = 's.product.season'
    _description = 'Mùa'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
