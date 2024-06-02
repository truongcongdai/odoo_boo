from odoo import models

from odoo.exceptions import UserError
class SReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        for r in self:
            # Thu ngân có quyền TẠO TRẢ HÀNG DO của cửa hàng mình
            if r.env.user.has_group('advanced_sale.s_boo_group_thu_ngan') and not r.env.user.has_group('base.group_system'):
                if r.picking_id and r.picking_id.s_warehouse_id:
                    if r.picking_id.s_warehouse_id.id not in r.env.user.boo_warehouse_ids.ids:
                        raise UserError('Bạn không thể trả hàng điều chuyển này.')
            # Tinh diem loyalty_points cua customer khi tra lai hang
            sale_order_obj = r.picking_id.sale_id
            if sale_order_obj:
                order_loyalty_points = sale_order_obj.loyalty_points
                partner_obj = sale_order_obj.partner_id
                if partner_obj:
                    partner_loyalty_points = partner_obj.loyalty_points
                    if partner_loyalty_points and order_loyalty_points and partner_loyalty_points >= order_loyalty_points:
                        r.picking_id.sale_id.partner_id.sudo().write({
                            'loyalty_points': partner_loyalty_points - order_loyalty_points
                        })
        return super(SReturnPicking, self).create_returns()
