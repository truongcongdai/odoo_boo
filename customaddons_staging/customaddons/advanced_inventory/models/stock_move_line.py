from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move.line'
    confirm_user_id = fields.Many2one('res.users', string='Người duyệt' , related="picking_id.confirm_user_id")

    transfer_type = fields.Selection([('in', 'Phiếu nhập'), ('out', 'Phiếu xuất')],
                                     string='Loại điều chuyển',
                                     related='picking_id.transfer_type', readonly=True)
    ma_san_pham = fields.Char(string="Mã sản phẩm", related='product_id.ma_san_pham', store=True)
    ma_cu = fields.Char(string="Mã cũ", related='product_id.ma_cu', store=True)

    def view_stock_move_line_by_group(self):
        # Nhóm Thu nhân
        if self.env.user.has_group('advanced_sale.s_boo_group_thu_ngan') and not self.env.user._is_admin():
            user_login = self.env.user
            # Lọc stock.move.line do user đó tạo, hoặc được add employee trong POS
            if user_login.boo_warehouse_ids:
                self.clear_caches()
                move_ids = self.env['stock.move.line'].sudo().search(['|', '|', ('picking_id.create_uid', '=', user_login.id),
                                                                      ('picking_id.location_id.warehouse_id_store', 'in', user_login.boo_warehouse_ids.ids),
                                                                      ('picking_id.location_dest_id.warehouse_id_store', 'in', user_login.boo_warehouse_ids.ids
                                                                       )]).ids
            else:
                move_ids = self.env['stock.move.line'].sudo().search([('picking_id.create_uid', '=', user_login.id)]).ids
            return{
                'name': _('Truy vết'),
                'view_mode': 'tree,kanban,pivot,form',
                'res_model': 'stock.move.line',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', move_ids)],
                'context': {'search_default_filter_last_12_months': 1,
                            'search_default_done': 1,
                            'search_default_groupby_product_id': 1,
                            'create': 0,
                            'delete': 0}
            }
        elif self.env.user.has_group('advanced_sale.s_boo_group_administration'):
            return{
                'name': _('Truy vết'),
                'view_mode': 'tree,kanban,pivot,form',
                'res_model': 'stock.move.line',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': {'search_default_filter_last_12_months': 1,
                            'search_default_done': 1,
                            'search_default_groupby_product_id': 1,
                            'create': 0,
                            'delete': 1}
            }
        else:
            return {
                'name': _('Truy vết'),
                'view_mode': 'tree,kanban,pivot,form',
                'res_model': 'stock.move.line',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': {'search_default_filter_last_12_months': 1,
                            'search_default_done': 1,
                            'search_default_groupby_product_id': 1,
                            'create': 0,
                            'delete': 0}
            }








