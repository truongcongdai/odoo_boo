from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    mapping_bravo_ids = fields.Many2many(
        comodel_name='bravo.stock.picking.mappings',
        string='Bravo Mappings',
    )
    s_date_completed = fields.Datetime(string='Ngày hoàn thành đơn hàng hoàn thành 1 phần', compute='_compute_s_date_completed', store=True)

    # def write(self, vals):
    #     warehouse_online_id = self.env['stock.warehouse'].sudo().search([('is_location_online', '=', True)], limit=1).lot_stock_id.s_transit_location_id.id
    #     location_online = self.env['stock.location'].sudo().search([('id', '=', warehouse_online_id), ('s_is_transit_location', '=', True)])
    #     picking_ids = self.picking_ids
    #     for rec in picking_ids:
    #         if rec.state == 'done':
    #             stock_move_ids = self.env['stock.move'].sudo().search([('picking_id', '=', rec.id)])
    #             for move in stock_move_ids:
    #                 if move.product_id.detailed_type == 'product' and (self.is_magento_order == True or self.return_order_id.is_magento_order == True):
    #                     transit_obj = self.env['s.transit.stock.quant'].sudo()
    #                     stock_transit = transit_obj.search([
    #                         ('product_id', '=', move.product_id.id), ('location_id', '=', location_online.id)
    #                     ], limit=1)
    #                     value = {
    #                         'location_id': location_online.id,
    #                         'product_id': move.product_id.id,
    #                         'available_quantity': 0,
    #                         'quantity': 0,
    #                         'to_sync_bravo': False
    #                     }
    #                     quantity = 0
    #                     if vals.get('sale_order_status'):
    #                         if stock_transit:
    #                             if vals.get('sale_order_status') in ('dang_xu_ly', 'dang_giao_hang'):
    #                                 quantity = stock_transit.quantity + move.product_uom_qty
    #                             elif vals.get('sale_order_status') in ('hoan_thanh', 'hoan_thanh_1_phan', 'giao_hang_that_bai', 'huy', 'closed'):
    #                                 quantity = stock_transit.quantity - move.product_uom_qty
    #                             if quantity < 0:
    #                                 quantity = 0
    #                             value.update({
    #                                 'available_quantity': quantity,
    #                                 'quantity': quantity,
    #                             })
    #                             stock_transit.sudo().unlink()
    #                             transit_obj.create(value)
    #                         else:
    #                             if vals.get('sale_order_status') == 'dang_xu_ly':
    #                                 value.update({
    #                                     'available_quantity': move.product_uom_qty,
    #                                     'quantity': move.product_uom_qty
    #                                 })
    #                             transit_obj.create(value)
    #     return super(SaleOrder, self).write(vals)

    @api.depends('completed_date')
    def _compute_s_date_completed(self):
        for rec in self:
            if rec.is_magento_order:
                if rec.completed_date:
                    comp_date = rec.completed_date
                    if rec.sale_order_status == 'hoan_thanh_1_phan':
                        do_return = rec.picking_ids.filtered(lambda l: l.transfer_type == 'in' and l.state not in ('done', 'cancel'))
                        if len(do_return):
                            rec.write({
                                's_date_completed': comp_date,
                                'completed_date': False
                            })

