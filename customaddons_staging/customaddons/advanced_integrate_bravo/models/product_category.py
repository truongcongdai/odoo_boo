from odoo import fields, models, api


class ProductCategoryInherit(models.Model):
    _inherit = 'product.category'
    bravo_id = fields.Integer(
        string='Bravo category')
