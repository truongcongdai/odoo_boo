from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class SReturnPickingInherit(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        new_picking_id, pick_type_id = super(SReturnPickingInherit, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        if new_picking:
            new_picking.sudo().write({
                'returned_picking_id': self.picking_id.id
            })
            if self.picking_id.is_inventory_receiving == True:
                new_picking.sudo().write({
                    'is_inventory_receiving': True
                })
        return new_picking_id, pick_type_id