from odoo import fields, models, api


class StockPickingInerht(models.Model):
    _inherit = 'stock.picking'
    s_warehouse_id = fields.Many2one('stock.warehouse', related="picking_type_id.warehouse_id")
    is_invisible_btn_cancel = fields.Boolean(compute='_compute_invisible_btn_cancel')

    def _compute_invisible_btn_cancel(self):
        self.is_invisible_btn_cancel = False
        return self.is_invisible_btn_cancel

