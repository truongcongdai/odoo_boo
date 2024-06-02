from odoo import fields, models, api


class SProductBrandBravoMapping(models.Model):
    _name = 's.product.brand.bravo.mapping'
    _description = 'Thương Hiệu mapping'

    s_first_character = fields.Char(string='Ký tự đầu tiên của mã cũ')
    s_bravo_lines = fields.Many2one('dong.hang', string='Tên dòng hàng - bravo')
    s_odoo_brand = fields.Many2one('s.product.brand', string='Brand - odoo')
    s_bravo_brand = fields.Many2one('s.product.brand', string='Brand - bravo')
