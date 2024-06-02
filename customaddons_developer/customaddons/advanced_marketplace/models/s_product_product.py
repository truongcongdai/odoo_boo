from odoo import fields, models


class SProductProduct(models.Model):
    _inherit = 'product.product'

    marketplace_sku = fields.Text("Marketplace SKU", track_visibility='always')
    is_merge_product = fields.Boolean("Gộp sản phẩm trên Marketplace", default=False, track_visibility='always')
    s_mkp_is_sku_ky_tu = fields.Boolean(default=False, string="Sửa đơn hàng Marketplace lỗi sku", track_visibility='always')
    s_mkp_sku_ky_tu = fields.Text(string="SKU Lỗi", track_visibility='always')