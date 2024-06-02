from odoo import fields, models, api


class DongHang(models.Model):
    _name = 'dong.hang'
    _description = 'Dòng Hàng'

    code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Tên')
