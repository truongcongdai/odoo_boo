from odoo import fields, models

class SResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    customer_rank_size = fields.Integer(string="Customer Rank Size", config_parameter='advanced_pos.get_customer_rank_limit', default=500)
    product_size = fields.Integer(string="Product Size",
                                        config_parameter='advanced_pos.get_product_limit', default=1000)
