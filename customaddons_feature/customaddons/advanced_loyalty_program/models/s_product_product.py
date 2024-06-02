from odoo import models, fields, api


class SLoyaltyProductProduct(models.Model):
    _inherit = 'product.product'

    s_loyalty_product_reward = fields.Boolean(string='Sản phẩm quy đổi điểm')

