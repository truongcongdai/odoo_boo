from odoo import _, api, fields, models


class SStockMoveInherit(models.Model):
    _inherit = "stock.move"

    is_push_tiktok_transfer_quantity = fields.Boolean(string="Is push tiktok transfer quantity", default=False)
    s_tiktok_transfer_quantity = fields.Float(string="Tiktok transfer quantity", default=0)
    s_tiktok_reserved_quantity = fields.Float(string="Tiktok reserved quantity", default=0)

    def write(self, vals):
        if vals.get('state'):
            for rec in self:
                picking = rec.sudo().picking_id
                if picking:
                    ##Hiện tại kho tiktok chỉ có duy nhất 1 kho -> sử dụng picking.warehouse_id
                    if not picking.sale_id and not picking.pos_order_id and not picking.s_tiktok_order_id and picking.s_warehouse_id.s_warehouse_tiktok_id:
                        ##Nếu kho xuất là kho hàng tiktok -> trừ đi số lượng
                        if picking.location_id.warehouse_id.e_commerce == 'tiktok' and picking.location_id.warehouse_id.s_warehouse_tiktok_id and not picking.location_id.s_is_transit_location and rec.product_id.is_synced_tiktok:
                            ## kho xuất là kho hàng tiktok và state chuyển sang assigned giữ tồn kho
                            if vals.get('state') == 'assigned':
                                #Lưu số lượng giữ trước
                                rec.s_tiktok_reserved_quantity = rec.reserved_availability
                                #
                                rec.s_tiktok_transfer_quantity = -rec.reserved_availability
                                rec.is_push_tiktok_transfer_quantity = True
                            elif vals.get('state') == 'cancel':
                                ##TH1: Nếu phiếu đã được push lên tiktok -> reserved = 0 -> push lại số lượng âm reserved đã đẩy trước đó
                                if rec.s_tiktok_transfer_quantity == 0 and rec.is_push_tiktok_transfer_quantity == False:
                                    rec.s_tiktok_transfer_quantity = rec.s_tiktok_reserved_quantity
                                    rec.is_push_tiktok_transfer_quantity = True
                                ##TH2: Nếu phiếu chưa được push lên tiktok -> reserved != 0 -> reserved = 0
                                else:
                                    rec.s_tiktok_transfer_quantity = 0
                                    rec.is_push_tiktok_transfer_quantity = False
                            elif vals.get('state') == 'done':
                                ##Nếu phiếu chưa được push lên tiktok -> reserved != 0 -> reserved = 0
                                if rec.s_tiktok_transfer_quantity != 0 and rec.is_push_tiktok_transfer_quantity:
                                    rec.s_tiktok_transfer_quantity = -rec.quantity_done
                                    rec.is_push_tiktok_transfer_quantity = True
                        ##Nếu kho nhập là kho hàng tiktok -> cộng thêm số lượng
                        elif picking.location_dest_id.warehouse_id.e_commerce == 'tiktok' and picking.location_dest_id.warehouse_id.s_warehouse_tiktok_id and not picking.location_dest_id.s_is_transit_location and rec.product_id.is_synced_tiktok:
                            if vals.get('state') == 'done':
                                rec.s_tiktok_transfer_quantity = rec.quantity_done
                                rec.is_push_tiktok_transfer_quantity = True
        return super(SStockMoveInherit, self).write(vals)
