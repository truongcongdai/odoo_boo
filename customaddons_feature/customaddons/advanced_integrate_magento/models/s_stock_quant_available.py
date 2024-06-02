from odoo import api, fields, models


class SStockQuantAvailable(models.Model):
    _name = 's.stock.quant.available'

    sku = fields.Char(string='Mã SKU sản phẩm')
    source = fields.Char(string='Kho')
    quantity = fields.Float(string='Số lượng')
    metadata = fields.Char(string='Lý do điều chuyển')
    transfer_type = fields.Selection([
        ('out', 'Phiếu xuất'),
        ('in', 'Phiếu nhập')
    ], string='Loại phiếu')
    state = fields.Selection([
        ('assigned', 'Sẵn sàng'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy')
    ], string='Trạng thái')
    back_order = fields.Boolean(string='DO dang dở')
