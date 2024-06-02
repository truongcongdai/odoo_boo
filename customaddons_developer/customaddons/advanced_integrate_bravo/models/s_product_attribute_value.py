from odoo import fields, models, api


class ProductAttributeValueInherit(models.Model):
    _inherit= 'product.attribute.value'
    _rec_name = 'code'