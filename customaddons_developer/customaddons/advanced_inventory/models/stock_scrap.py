from odoo import fields, models


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    mau_sac = fields.Char(related='product_id.mau_sac', store=True)
    kich_thuoc = fields.Char(related='product_id.kich_thuoc', store=True)
    thuong_hieu = fields.Many2one('s.product.brand', string="Thương hiệu", related='product_id.thuong_hieu', store=True)
    category_id = fields.Many2one('product.category', string='Nhóm sản phẩm', related='product_id.categ_id', store=True)
