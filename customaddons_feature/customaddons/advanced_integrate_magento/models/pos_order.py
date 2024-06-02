from odoo import fields, models


class PoSOrder(models.Model):
    _inherit = ['pos.order']

    pos_mapping_ids = fields.One2many(
        comodel_name='channel.pos.mappings',
        inverse_name='pos_order_id',
        string='Mappings',
        readonly=True
    )
