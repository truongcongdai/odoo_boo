from odoo import fields, models, api


class ProductAttributeInherit(models.Model):
    _inherit = 'product.attribute'
    bravo_id = fields.Integer(string='Bravo Attribute')

