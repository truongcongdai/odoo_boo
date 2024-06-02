from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import urllib.parse
import base64, requests
import time
import json


class SStockPickings(models.Model):
    _inherit = "stock.picking"

    picking_lazada_status = fields.Selection([("ready_to_ship", "Hoàn tất đóng gói"),
                                              ("ready_to_ship_pending", "Chờ giao hàng"),
                                              ("delivered", "Giao hàng thành công"),
                                              ("info_st_driver_assigned", "Người vận chuyển"),
                                              ("cancelled", 'Giao hàng thất bại')
                                              ], string="Trạng thái giao hàng Lazada")
    marketplace_lazada_order_status = fields.Selection([
        ("unpaid", "Mới"),
        ("pending", "Mới"),
        ("packed", "Đang xử lý"),
        ('repacked', "Đang xử lý"),
        ("ready_to_ship_pending", "Đang xử lý"),
        ("ready_to_ship", "Đang giao hàng"),
        ("shipped", "Hoàn thành"),
        ("delivered", "Hoàn thành"),
        ("returned", "Hoàn thành"),
        ("canceled", "Hủy")
    ], string="Tình trạng đơn hàng Lazada", related='sale_id.marketplace_lazada_order_status')
    package_lazada_id = fields.Char("Package Lazada ID")
    is_do_lazada_return = fields.Boolean("Là DO Lazada Return")
    lazada_order_id = fields.Char(string='Mã đơn hàng gốc Lazada', related='sale_id.lazada_order_id')
    reverse_order_id = fields.Char(string="Mã đổi trả đơn hàng Lazada", related='sale_id.reverse_order_id')

    @api.depends('sale_id.is_lazada_order')
    def _compute_invisible_btn_cancel(self):
        self.is_invisible_btn_cancel = super(SStockPickings, self)._compute_invisible_btn_cancel()
        if self.sale_id.is_lazada_order and not self.is_invisible_btn_cancel:
            self.is_invisible_btn_cancel = True
        return self.is_invisible_btn_cancel

    def button_validate(self):
        for rec in self:
            if rec.sale_id.marketplace_lazada_order_status == 'unpaid':
                raise ValidationError('Không thể Xác nhận DO Lazada.')
            if rec.sale_id.marketplace_lazada_order_status == 'pending':
                order_items = self.env['sale.order'].sudo().get_lazada_order_item(order_id=rec.sale_id.lazada_order_id)
                if order_items:
                    order_item_ids = []
                    for item in order_items:
                        if item.get('order_item_id'):
                            order_item_ids.append(item.get('order_item_id'))
                    self.env['sale.order'].sudo().set_lazada_order(order=rec.sale_id, order_item_ids=order_item_ids)
        return super(SStockPickings, self).button_validate()

    def btn_open_shipping_label_lazada(self):
        if self.package_lazada_id:
            print_error, packages = [], []
            for rec in self:
                if rec.package_lazada_id:
                    packages.append({
                        "package_id": rec.package_lazada_id
                    })
            url_api = "/order/package/document/get"
            param = {
                "getDocumentReq": {
                    "doc_type": "PDF",
                    "packages": packages
                    }
            }
            req = self.env['base.integrate.lazada']._post_data_lazada(api=url_api, parameters=param)
            if req['code'] == '0':
                if "error_msg" not in req:
                    url = req.get('result').get('data').get('pdf_url')
                    return {
                        'name': 'Shipping Document',
                        'type': 'ir.actions.act_url',
                        'url': url,
                        'target': 'new',
                    }
                else:
                    raise ValidationError(req.get("error_msg"))
        else:
            raise ValidationError("DO chưa có Package ID. Vui lòng kiểm tra lại!")
