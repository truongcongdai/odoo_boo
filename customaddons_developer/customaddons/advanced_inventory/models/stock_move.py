from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    stock_package_ids = fields.Many2many('s.stock.picking.package', string='Kiện hàng')
    is_transfer_in = fields.Boolean(string='Is transfer in', compute='_compute_check_transfer_in')
    is_package = fields.Boolean(default=False)
    inventory_qty_note = fields.Char(string='Số lượng còn trong kho')
    ma_san_pham = fields.Char(related='product_id.ma_san_pham')
    ma_cu = fields.Char(related='product_id.ma_cu')
    s_date_done = fields.Datetime(string='Ngày hoàn thành', compute='_compute_picking_id', store=True)
    s_transfer_note = fields.Char(string='Ghi chú của phiếu điều chuyển', compute='_compute_picking_id', store=True)
    # s_picking_date_done = fields.Datetime(string='Ngày hoàn thành', compute='_compute_picking_id', store=True)
    # s_picking_transfer_note = fields.Char(string='Ghi chú của phiếu điều chuyển', compute='_compute_picking_id', store=True)
    initial_need_qty = fields.Float(string='Đề xuất', compute='_compute_initial_need_quantity')

    @api.depends('picking_id', 'picking_id.date_done', 'picking_id.transfer_note')
    def _compute_picking_id(self):
        for rec in self:
            rec.sudo().write({
                's_date_done': rec.picking_id.date_done,
                's_transfer_note': rec.picking_id.note
            })

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        if (self.product_uom_qty % 1 != 0):
            raise UserError(_('Nhu cầu phải là số nguyên.'))

    @api.onchange('quantity_done')
    def _onchange_quantity_done(self):
        if (self.quantity_done % 1 != 0):
            raise UserError(_('Hoàn thành phải là số nguyên.'))

    def _compute_check_transfer_in(self):
        for rec in self:
            if rec.picking_id.transfer_in_id:
                rec.is_transfer_in = True
            else:
                rec.is_transfer_in = False

    @api.depends('picking_id.transfer_in_id', 'picking_id.transfer_out_id')
    def _compute_initial_need_quantity(self):
        for rec in self:
            if not rec.picking_id.transfer_in_id or not rec.picking_id.transfer_out_id:
                rec.initial_need_qty = 0
            if rec.picking_id.transfer_in_id:
                if rec.picking_id.transfer_in_id.transfer_line:
                    for line in rec.picking_id.transfer_in_id.transfer_line:
                        if line.product_id == rec.product_id:
                            rec.initial_need_qty = line.qty_expect
            if rec.picking_id.transfer_out_id:
                if rec.picking_id.transfer_out_id.transfer_line:
                    for line in rec.picking_id.transfer_out_id.transfer_line:
                        if line.product_id == rec.product_id:
                            rec.initial_need_qty = line.qty_expect

    def write(self, vals):
        if 'is_package' in vals:
            if not vals['is_package']:

                for line in self.stock_package_ids:
                    for product in line.product_lines_ids:
                        if self.id == product.move_ids_without_package_id.id:
                            product.unlink()
                self.stock_package_ids = [(6, 0, [])]
            else:
                self.quantity_done = 0
        res = super(StockMove, self).write(vals)
        return res

    # @api.onchange('is_package')
    # def onchange_is_package(self):
    #     if not self.is_package:
    #         self.quantity_done = 0
    #         for line in self.stock_package_ids:
    #             for product in line.product_lines_ids:
    #                 if product.move_ids_without_package_id.id in self.ids:
    #                     line.product_lines_ids = [(3, 0, 0)]
    #         self.stock_package_ids = [(6, 0, [])]

    def action_add_to_package(self):
        return {
            'name': _('Thêm kiện hàng'),
            'view_mode': 'form',
            'res_model': 's.choice.stock.package',
            'type': 'ir.actions.act_window',
            'context': {'default_stock_picking_id': self.picking_id.ids,
                        'default_move_ids_without_package_id': self.id,
                        'default_stock_picking_package': self.picking_id.stock_package_ids.ids
                        },
            'target': 'new',
        }

    @api.onchange('move_line_ids')
    def onchange_move_line_ids_check_s_transfer(self):
        for rec in self:
            if rec.picking_id.transfer_out_id:
                move_out_expect_dict = {}
                for e in rec.picking_id.transfer_out_id.transfer_line:
                    move_out_expect_dict[e.product_id.id] = e.qty_expect - e.qty_out_real
                move_out_done_dict = {}
                for e in rec.move_line_ids:
                    if e.product_id.id not in move_out_done_dict:
                        move_out_done_dict[e.product_id.id] = e.qty_done
                    else:
                        move_out_done_dict[e.product_id.id] += e.qty_done
                for product_id in move_out_done_dict:
                    if product_id not in move_out_done_dict:
                        raise UserError('Bạn đang xuất kho sản phẩm không có trong lệnh điều chuyển')
                    elif move_out_done_dict[product_id] > move_out_expect_dict[product_id]:
                        raise UserError(
                            'Không điều chuyển vượt số lượng đề xuất. Vui lòng kiểm tra lại số lượng hoàn thành')
            if rec.picking_id.transfer_in_id:
                move_out_done_dict = {}
                for e in rec.picking_id.transfer_in_id.transfer_line:
                    move_out_done_dict[e.product_id.id] = e.qty_out_real - e.qty_in_real
                move_in_done_dict = {}
                for e in rec.move_line_ids:
                    if e.product_id.id not in move_in_done_dict:
                        move_in_done_dict[e.product_id.id] = e.qty_done
                    else:
                        move_in_done_dict[e.product_id.id] += e.qty_done
                for product_id in move_in_done_dict:
                    if product_id not in move_out_done_dict:
                        raise UserError('Bạn đang nhập kho sản phẩm không có trong lệnh điều chuyển')
                    elif move_in_done_dict[product_id] > move_out_done_dict[product_id]:
                        raise UserError('Bạn không thể nhận nhiều hơn số lượng xuất trong phiếu xuất')

    def view_stock_move_by_group(self):
        if self.env.user.has_group('advanced_sale.s_boo_group_thu_ngan') and not self.env.user._is_admin():
            user_login = self.env.user
            if user_login.boo_warehouse_ids:
                self.clear_caches()
                move_ids = self.env['stock.move'].sudo().search(
                    ['|',
                     ('picking_id.location_id.warehouse_id_store', 'in', user_login.boo_warehouse_ids.ids),
                     ('picking_id.location_dest_id.warehouse_id_store', 'in', user_login.boo_warehouse_ids.ids
                      )]).ids
            else:
                move_ids = self.env['stock.move'].sudo().search(
                    [('picking_id.create_uid', '=', user_login.id)]).ids
            return {
                'name': _('Dịch chuyển kho'),
                'view_mode': 'tree,kanban,pivot,form',
                'views': [(self.env.ref('stock.view_move_tree').id, 'tree'),
                          (self.env.ref('stock.view_move_form').id, 'form')],
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', move_ids)],
                'context': {'search_default_filter_last_12_months': 1,
                            'search_default_done': 1,
                            'search_default_groupby_location_id': 1,
                            'create': 0,
                            'delete': 0}
            }
        elif self.env.user.has_group('advanced_sale.s_boo_group_administration'):
            return {
                'name': _('Dịch chuyển kho'),
                'view_mode': 'tree,kanban,pivot,form',
                'views': [(self.env.ref('stock.view_move_tree').id, 'tree'),
                          (self.env.ref('stock.view_move_form').id, 'form')],
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': {'search_default_filter_last_12_months': 1,
                            'search_default_done': 1,
                            'search_default_groupby_location_id': 1,
                            'create': 0,
                            'delete': 1}
            }
        else:
            return {
                'name': _('Dịch chuyển kho'),
                'view_mode': 'tree,kanban,pivot,form',
                'views': [(self.env.ref('stock.view_move_tree').id, 'tree'),
                          (self.env.ref('stock.view_move_form').id, 'form')],
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': {'search_default_filter_last_12_months': 1,
                            'search_default_done': 1,
                            'search_default_groupby_location_id': 1,
                            'create': 0,
                            'delete': 0}
            }
