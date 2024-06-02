from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    time_product_expired = fields.Integer(string='Thời gian cảnh báo sản phẩm tồn kho quá hạn')
