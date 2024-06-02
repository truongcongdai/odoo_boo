from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = ['stock.location']

    s_is_inventory_adjustment_location = fields.Boolean(
        string='Kho ảo chứa chênh lệch?',
        compute='_compute_is_inventory_adjustment_location',
        store=True
    )
    is_inventory_unsync = fields.Boolean(string="Không đồng bộ dữ liệu phiếu sang bravo")

    @api.depends('usage')
    def _compute_is_inventory_adjustment_location(self):
        for rec in self:
            is_inventory_adjustment_location = False
            if rec.usage == 'inventory':
                is_inventory_adjustment_location = True
            rec.s_is_inventory_adjustment_location = is_inventory_adjustment_location
