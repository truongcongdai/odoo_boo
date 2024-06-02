from odoo import api, fields, models


class ChannelPOSMappings(models.TransientModel):
    _inherit = 'channel.mappings'
    _name = 'channel.pos.mappings'
    _rec_name = 'pos_order_id'
    _description = 'Pos Order Mappings'

    store_pos_order_id = fields.Char(
        string='Remote PoS Order ID'
    )
    pos_order_id = fields.Many2one(
        comodel_name='pos.order',
        string='Order',
    )
    odoo_pos_order_id = fields.Integer(
        string='PoS Order ID'
    )
    odoo_partner_id = fields.Many2one(
        related='pos_order_id.partner_id',
        store=True
    )

    @api.onchange('pos_order_id')
    def _onchange_pos_order_id(self):
        if self.pos_order_id:
            self.odoo_pos_order_id = self.pos_order_id.id

    def _compute_name(self):
        for record in self:
            record.name = record.pos_order_id and record.pos_order_id.name or 'Deleted'
