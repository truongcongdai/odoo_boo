from odoo import fields, models, api


class SSaleReport(models.Model):
    _inherit = 'sale.report'

    mau_sac_sp = fields.Char(
        string='Màu sắc',
        compute="_compute_product_id",
        store=True
    )
    kich_thuoc_sp = fields.Char(
        string='Kích thước',
        compute="_compute_product_id",
        store=True
    )
    thuong_hieu_id = fields.Many2one(
        's.product.brand',
        string='Thương hiệu',
        compute="_compute_product_tmpl_id",
        store=True
    )
    chuong_trinh_khuyen_mai_order = fields.Char(string='Chương trình khuyến mãi')
    date_order_sale_filter = fields.Datetime(string="Date filter")
    tong_chiet_khau = fields.Float(string='Tổng chiết khấu phân bổ và trực tiếp')
    so_luong_san_pham = fields.Integer(string='Số lượng sản phẩm')
    gia_tong = fields.Float(string='Giá tổng')

    @api.depends('product_id')
    def _compute_product_id(self):
        for r in self:
            r.kich_thuoc_sp = None
            r.mau_sac_sp = None
            if r.product_id:
                r.kich_thuoc_sp = r.product_tmpl_id.kich_thuoc
                r.mau_sac_sp = r.product_tmpl_id.mau_sac

    @api.depends('product_tmpl_id')
    def _compute_product_tmpl_id(self):
        for r in self:
            r.thuong_hieu_id = None
            if r.product_tmpl_id:
                if r.product_tmpl_id.thuong_hieu:
                    r.thuong_hieu_id = r.product_tmpl_id.thuong_hieu.id

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['thuong_hieu_id'] = ", t.thuong_hieu AS thuong_hieu_id"
        fields['kich_thuoc_sp'] = ", p.kich_thuoc AS kich_thuoc_sp"
        fields['mau_sac_sp'] = ", p.mau_sac AS mau_sac_sp"
        fields['chuong_trinh_khuyen_mai_order'] = ", s.s_promo_program_m2 AS chuong_trinh_khuyen_mai_order"
        fields['date_order_sale_filter'] = ",s.date_order_sale_filter as date_order_sale_filter"
        fields['tong_chiet_khau'] = ", (l.boo_total_discount+l.boo_total_discount_percentage) AS tong_chiet_khau"
        fields['so_luong_san_pham'] = ", SUM(l.product_uom_qty) AS so_luong_san_pham"
        fields['gia_tong'] = ", SUM(l.product_uom_qty*l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS gia_tong"
        groupby += ', t.thuong_hieu, p.kich_thuoc, p.mau_sac, l.boo_total_discount, l.boo_total_discount_percentage, s.s_promo_program_m2'
        return super(SSaleReport, self)._query(with_clause, fields, groupby, from_clause)
