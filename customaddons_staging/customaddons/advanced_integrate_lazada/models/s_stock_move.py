from odoo import _, api, fields, models


class StockMoveInherit(models.Model):
    _inherit = "stock.move"

    is_push_lazada_transfer_quantity = fields.Boolean(string="Is push lazada transfer quantity", default=False)
    s_lazada_transfer_quantity = fields.Float(string="lazada transfer quantity", default=0)
    s_lazada_reserved_quantity = fields.Float(string="lazada reserved quantity", default=0)

    def write(self, vals):
        if vals.get('state'):
            for rec in self:
                picking = rec.sudo().picking_id
                if picking:
                    if not picking.sale_id and not picking.pos_order_id and not picking.lazada_order_id and picking.s_warehouse_id.is_push_lazada:
                        if picking.location_id.warehouse_id.e_commerce == 'lazada' and picking.location_id.warehouse_id.is_push_lazada and not picking.location_id.s_is_transit_location and rec.product_id.s_lazada_is_mapped_product:
                            if vals.get('state') == 'assigned':
                                #Lưu số lượng giữ trước
                                rec.s_lazada_reserved_quantity = rec.reserved_availability
                                #
                                rec.s_lazada_transfer_quantity = -rec.reserved_availability
                                rec.is_push_lazada_transfer_quantity = True
                            elif vals.get('state') == 'cancel':
                                ##TH1: Nếu phiếu đã được push lên lazada -> reserved = 0 -> push lại số lượng âm reserved đã đẩy trước đó
                                if rec.s_lazada_transfer_quantity == 0 and rec.is_push_lazada_transfer_quantity == False:
                                    rec.s_lazada_transfer_quantity = rec.s_lazada_reserved_quantity
                                    rec.is_push_lazada_transfer_quantity = True
                                ##TH2: Nếu phiếu chưa được push lên lazada -> reserved != 0 -> reserved = 0
                                else:
                                    rec.s_lazada_transfer_quantity = 0
                                    rec.is_push_lazada_transfer_quantity = False
                            elif vals.get('state') == 'done':
                                ##Nếu phiếu chưa được push lên lazada -> reserved != 0 -> reserved = 0
                                if rec.s_lazada_transfer_quantity != 0 and rec.is_push_lazada_transfer_quantity:
                                    rec.s_lazada_transfer_quantity = -rec.quantity_done
                                    rec.is_push_lazada_transfer_quantity = True
                        ##Nếu kho nhập là kho hàng lazada -> cộng thêm số lượng
                        elif picking.location_dest_id.warehouse_id.e_commerce == 'lazada' and picking.location_dest_id.warehouse_id.is_push_lazada and not picking.location_dest_id.s_is_transit_location and rec.product_id.s_lazada_is_mapped_product:
                            if vals.get('state') == 'done':
                                rec.s_lazada_transfer_quantity = rec.quantity_done
                                rec.is_push_lazada_transfer_quantity = True
        return super(StockMoveInherit, self).write(vals)
