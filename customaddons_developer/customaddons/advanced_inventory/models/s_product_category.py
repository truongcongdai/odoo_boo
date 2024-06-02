from odoo import fields, models, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    time_quantity_warning = fields.Integer(string='Thời gian cảnh báo sản phẩm tồn kho quá hạn')
