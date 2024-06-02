from odoo import _, api, fields, models


class ChannelOrderMappings(models.Model):
    _inherit = 'channel.order.mappings'

    store_order_id = fields.Char(
        required=False
    )
