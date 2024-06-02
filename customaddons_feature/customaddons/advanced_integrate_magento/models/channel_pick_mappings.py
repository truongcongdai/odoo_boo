from odoo import _, api, fields, models


class ChannelPickMappings(models.TransientModel):
    _name = 'channel.pick.mappings'
    _inherit = ['channel.mappings']
    _description = 'Channel Pick Mappings'

    store_stock_pick_id = fields.Char(
        string='Remote Delivery Order ID'
    )
    stock_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Delivery Order',
        domain=[('picking_type_code', '=', 'outgoing')]
    )
    odoo_stock_picking_id = fields.Integer(
        string='Delivery Order ID'
    )
    odoo_source_document = fields.Char(
        related='stock_picking_id.origin',
        store=True
    )

    @api.onchange('stock_picking_id')
    def _onchange_pos_order_id(self):
        if self.stock_picking_id:
            self.odoo_stock_picking_id = self.stock_picking_id.id

    def _compute_name(self):
        for record in self:
            record.name = record.stock_picking_id and record.stock_picking_id.name or _('Deleted')
