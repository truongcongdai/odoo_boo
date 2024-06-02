from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    online_order_id = fields.Char(string='Order ID on website')
    completed_time = fields.Datetime(compute='_compute_picking_date', store=True)
    store_code = fields.Char(string='Mã cửa hàng')
    warehouse_code = fields.Char(string='S Ware House ID', compute="_compute_s_warehouse_id")

    @api.depends(
        'picking_ids',
        'picking_ids.state',
        'picking_ids.date_done'
    )
    def _compute_picking_date(self):
        for res in self:
            if not res.is_magento_order:
                res.completed_time = False
                if res.picking_ids and len(res.picking_ids.filtered(lambda sp: sp.state == 'done')) == len(res.picking_ids):
                    list_date_done = res.picking_ids.filtered(lambda p: p.date_done is not False).mapped('date_done')
                    if len(list_date_done)>0:
                        res.completed_time = max(list_date_done)

    def _compute_s_warehouse_id(self):
        for rec in self:
            rec.warehouse_code = ''
            stock_picking = self.env['stock.picking'].search([('sale_id', '=', rec.id), ('state', '=', 'done')])
            for wh in stock_picking:
                rec.warehouse_code += str(wh.location_id.warehouse_id.code)