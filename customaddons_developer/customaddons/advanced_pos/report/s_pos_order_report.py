from odoo import fields, models, api


class SPosOrderReport(models.Model):
    _inherit = 'report.pos.order'

    thuong_hieu_name = fields.Many2one(
        's.product.brand',
        string='Thương hiệu',
        compute="_compute_product_tmpl_id",
        store=True)
    # coupon_program_name = fields.Char(string='CTKM')
    customer_ranked = fields.Char(string='Hạng', store=True)
    # doanh_thu = fields.Float(
    #     string='Doanh thu'
    # )
    tong_chiet_khau = fields.Float(
        string='Tổng chiết khấu phân bổ và trực tiếp'
    )
    gia_tong = fields.Float(
        string='Giá tổng'
    )
    doanh_thu_chuan = fields.Float(
        string='Doanh thu (Tổng doanh thu - chiết khấu phân bổ)'
    )
    tracking = fields.Float(
        string='Tracking'
    )
    so_luong_san_pham = fields.Integer(
        string='Số lượng sản phẩm'
    )
    date_order_pos_filter = fields.Datetime(string="Date filter")

    @api.depends('product_tmpl_id')
    def _compute_product_tmpl_id(self):
        for r in self:
            r.thuong_hieu_id = None
            if r.product_tmpl_id:
                if r.product_tmpl_id.thuong_hieu:
                    r.thuong_hieu_id = r.product_tmpl_id.thuong_hieu.name

    # @api.depends('order_id')
    # def _compute_order_id(self):
    #     for r in self:
    #         r.coupon_program_name = None
    #         if r.order_id:
    #             r.coupon_program_name = r.order_id.applied_promotion_program

    # def _select(self):
    #     return super(SPosOrderReport, self)._select() + ",pt.thuong_hieu AS thuong_hieu_name, " \
    #                                                     "s.date_order_pos_filter AS date_order_pos_filter," \
    #                                                     "s.customer_ranked AS customer_ranked," \
    #                                                     "l.program_name AS coupon_program_name, " \
    #                                                     "(l.boo_total_discount+l.boo_total_discount_percentage) AS tong_chiet_khau, " \
    #                                                     "SUM(l.price_subtotal_incl / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS doanh_thu," \
    #                                                     "SUM(CASE WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL THEN l.qty*l.s_lst_price ELSE 0 END) AS gia_tong," \
    #                                                     "SUM(CASE WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL THEN l.qty ELSE 0 END ) AS so_luong_san_pham"

    def _select(self):
        return super(SPosOrderReport, self)._select() + ",pt.thuong_hieu AS thuong_hieu_name, " \
                                                        "s.date_order_pos_filter AS date_order_pos_filter," \
                                                        "s.customer_ranked AS customer_ranked," \
                                                        "SUM(CASE " \
                                                        "WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL THEN boo_total_discount +l.boo_total_discount_percentage ELSE 0 END) AS tong_chiet_khau, " \
                                                        "SUM(CASE " \
                                                        "WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price > l.price_unit and l.price_unit > 0 THEN l.qty*l.s_lst_price " \
                                                        "WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price <= l.price_unit THEN l.qty*l.price_unit " \
                                                        "ELSE 0 END) AS gia_tong," \
                                                        "SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND (p.s_loyalty_product_reward = False OR p.s_loyalty_product_reward IS NULL) THEN l.qty ELSE 0 END ) AS so_luong_san_pham," \
                                                        "SUM(CASE " \
                                                        "WHEN l.program_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND l.boo_total_discount_percentage != 0 THEN l.price_subtotal_incl - l.boo_total_discount_percentage " \
                                                        "WHEN (l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True) AND l.boo_total_discount_percentage != 0 THEN l.boo_total_discount_percentage " \
                                                        "WHEN l.program_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND (l.boo_total_discount_percentage=0 or l.boo_total_discount_percentage is null) THEN l.price_subtotal_incl ELSE 0 END) AS doanh_thu_chuan," \
                                                        "SUM(CASE " \
                                                        "WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price > l.price_unit AND l.price_unit !=0 THEN l.qty*l.s_lst_price " \
                                                        "WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price <= l.price_unit THEN l.qty*l.price_unit " \
                                                        "ELSE 0 END) - " \
                                                        "SUM(CASE " \
                                                        "WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND l.boo_total_discount_percentage != 0 THEN l.price_subtotal_incl - l.boo_total_discount_percentage " \
                                                        "WHEN (l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True) AND l.boo_total_discount_percentage != 0 THEN l.boo_total_discount_percentage " \
                                                        "WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND (l.boo_total_discount_percentage=0 or l.boo_total_discount_percentage is null or l.is_product_service=True) THEN l.price_subtotal_incl ELSE 0 END) AS tracking"


    def _group_by(self):
        return super(SPosOrderReport,
                     self)._group_by() + ",pt.thuong_hieu, l.program_name, s.customer_ranked,l.boo_total_discount,l.boo_total_discount_percentage,l.price_subtotal_incl"

    def _from(self):
        return super(SPosOrderReport, self)._from() + "LEFT JOIN s_product_brand br ON (pt.thuong_hieu=br.id)"
