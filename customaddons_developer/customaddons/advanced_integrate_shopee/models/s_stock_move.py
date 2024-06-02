import datetime
import json
from json import dumps
import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import base64
import time


class SStockMove(models.Model):
    _inherit = "stock.move"
    s_shopee_transfer_quantity = fields.Integer(
        string='Shopee Transfer Quantity',
        required=False)
    is_push_shopee_transfer_quantity = fields.Boolean(
        string='Đã push transfer lên Shopee',
        default=False, copy=False)
    s_shopee_reserved_quantity = fields.Float(string="Shopee reserved quantity", default=0)

    def write(self, vals):
        if vals.get('state'):
            for rec in self:
                picking = rec.sudo().picking_id
                if picking:
                    ##Hiện tại kho shopee chỉ có duy nhất 1 kho mà kho lại không có id -> sử dụng picking.s_warehouse_id
                    if not picking.sale_id and not picking.pos_order_id and not picking.is_do_shopee and not picking.s_shopee_id_order and picking.s_warehouse_id.s_shopee_is_mapping_warehouse:
                        ##Nếu kho xuất là kho hàng shopee -> trừ đi số lượng
                        if picking.location_id.warehouse_id.e_commerce == 'shopee' and picking.location_id.warehouse_id.s_shopee_is_mapping_warehouse and rec.product_id.s_shopee_is_synced and picking.location_id.warehouse_id.lot_stock_id.id == picking.location_id.id:
                            ## kho xuất là kho hàng tiktok và state chuyển sang assigned giữ tồn kho
                            if vals.get('state') == 'assigned':
                                # Lưu số lượng giữ trước
                                rec.s_shopee_reserved_quantity = rec.reserved_availability
                                rec.s_shopee_transfer_quantity = -rec.reserved_availability
                                rec.is_push_shopee_transfer_quantity = True
                            elif vals.get('state') == 'cancel':
                                ##TH1: Nếu phiếu đã được push lên shopee -> reserved = 0 -> push lại số lượng âm reserved đã đẩy trước đó
                                if rec.s_shopee_transfer_quantity == 0 and rec.is_push_shopee_transfer_quantity == False:
                                    rec.s_shopee_transfer_quantity = rec.s_shopee_reserved_quantity
                                    rec.is_push_shopee_transfer_quantity = True
                                ##TH2: Nếu phiếu chưa được push lên shopee -> reserved != 0 -> reserved = 0
                                else:
                                    rec.s_shopee_transfer_quantity = 0
                                    rec.is_push_shopee_transfer_quantity = False
                            elif vals.get('state') == 'done':
                                ##Nếu phiếu chưa được push lên shopee -> reserved != 0 -> reserved = 0
                                if rec.s_shopee_transfer_quantity != 0 and rec.is_push_shopee_transfer_quantity:
                                    rec.s_shopee_transfer_quantity = -rec.quantity_done
                                    rec.is_push_shopee_transfer_quantity = True
                        ##Nếu kho nhập là kho hàng tiktok -> cộng thêm số lượng
                        elif picking.location_dest_id.warehouse_id.e_commerce == 'shopee' and picking.location_dest_id.warehouse_id.s_shopee_is_mapping_warehouse and not picking.location_dest_id.s_is_transit_location and rec.product_id.s_shopee_is_synced:
                            if vals.get('state') == 'done':
                                rec.s_shopee_transfer_quantity = rec.quantity_done
                                rec.is_push_shopee_transfer_quantity = True
        return super(SStockMove, self).write(vals)
