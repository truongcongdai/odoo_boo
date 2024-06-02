# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class PosOrderReport(models.Model):
    _name = "report.pos.order.program"
    _description = "Point of Sale Orders Report Program"
    _auto = False
    _order = 'date desc'

    date = fields.Datetime(string='Order Date', readonly=True)
    order_id = fields.Many2one('pos.order', string='Đơn hàng', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Khách hàng', readonly=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Sản phẩm template', readonly=True)
    state = fields.Selection(
        [('draft', 'New'), ('paid', 'Paid'), ('done', 'Posted'),
         ('invoiced', 'Invoiced'), ('cancel', 'Cancelled')],
        string='Status')
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    price_total = fields.Float(string='Thành tiền chưa tính chiết khấu', readonly=True)
    price_sub_total = fields.Float(string='Subtotal w/o discount', readonly=True)
    total_discount = fields.Float(string='Tổng chiết khấu', readonly=True)
    average_price = fields.Float(string='Average Price', readonly=True, group_operator="avg")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    nbr_lines = fields.Integer(string='Đếm dòng bán hàng', readonly=True)
    product_qty = fields.Integer(string='Số lượng sản phẩm', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    delay_validation = fields.Integer(string='Hoãn xác nhận')
    product_categ_id = fields.Many2one('product.category', string='Nhóm sản phẩm', readonly=True)
    invoiced = fields.Boolean(readonly=True)
    config_id = fields.Many2one('pos.config', string='Point of Sale', readonly=True)
    pos_categ_id = fields.Many2one('pos.category', string='PoS Category', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    margin = fields.Float(string='Biên lợi nhuận', readonly=True)

    coupon_program_name = fields.Char(string='CTKM')
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
    quantity_order = fields.Integer('Số lượng đơn hàng')

    @api.depends('product_tmpl_id')
    def _compute_product_tmpl_id(self):
        for r in self:
            r.thuong_hieu_id = None
            if r.product_tmpl_id:
                if r.product_tmpl_id.thuong_hieu:
                    r.thuong_hieu_id = r.product_tmpl_id.thuong_hieu.name

    def _select(self):
        return """
            SELECT
                MIN(l.id) AS id,
                COUNT(*) AS nbr_lines,
                s.date_order AS date,
                SUM(l.qty) AS product_qty,
                SUM(l.qty * l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS price_sub_total,
                SUM(ROUND((l.qty * l.price_unit) * (100 - l.discount) / 100 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places)) AS price_total,
                SUM((l.qty * l.price_unit) * (l.discount / 100) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS total_discount,
                CASE
                    WHEN SUM(l.qty * u.factor) = 0 THEN NULL
                    ELSE (SUM(l.qty*l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END)/SUM(l.qty * u.factor))::decimal
                END AS average_price,
                SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
                s.id as order_id,
                s.partner_id AS partner_id,
                s.state AS state,
                s.user_id AS user_id,
                s.company_id AS company_id,
                s.sale_journal AS journal_id,
                l.product_id AS product_id,
                pt.categ_id AS product_categ_id,
                p.product_tmpl_id,
                ps.config_id,
                pt.pos_categ_id,
                s.pricelist_id,
                s.session_id,
                s.account_move IS NOT NULL AS invoiced,
                SUM(l.price_subtotal - l.total_cost / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS margin,
                s.date_order_pos_filter AS date_order_pos_filter,
                s.customer_ranked AS customer_ranked,
                l.program_name AS coupon_program_name, 
                SUM(CASE WHEN l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True THEN (1/l.quantity_program_duplicate) END) AS quantity_order,
                SUM(CASE WHEN (l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True) THEN abs(l.qty*l.price_unit) END) AS tong_chiet_khau,
                SUM(CASE WHEN l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True THEN abs(s.amount_total) / l.quantity_program_duplicate + abs(l.qty*l.price_unit) END) AS gia_tong,
                SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL THEN l.qty ELSE 0 END ) AS so_luong_san_pham,
                SUM(CASE WHEN (l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True) AND (l.boo_total_discount_percentage = 0 OR l.boo_total_discount_percentage is null) THEN s.amount_total / l.quantity_program_duplicate END) AS doanh_thu_chuan,
                SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price > l.price_unit AND l.price_unit !=0 THEN l.qty*l.s_lst_price WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price <= l.price_unit THEN l.qty*l.price_unit ELSE 0 END) - SUM(CASE WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND l.boo_total_discount_percentage != 0 THEN l.price_subtotal_incl - l.boo_total_discount_percentage WHEN (l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True) AND l.boo_total_discount_percentage != 0 THEN l.boo_total_discount_percentage WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND (l.boo_total_discount_percentage=0 or l.boo_total_discount_percentage is null or l.is_product_service=True) THEN l.price_subtotal_incl ELSE 0 END) AS tracking
        """

    def _from(self):
        return """
            FROM pos_order_line AS l
                INNER JOIN pos_order s ON (s.id=l.order_id)
                LEFT JOIN product_product p ON (l.product_id=p.id)
                LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
                LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                LEFT JOIN res_company co ON (s.company_id=co.id)
                LEFT JOIN res_currency cu ON (co.currency_id=cu.id)
                LEFT JOIN s_product_brand br ON (pt.thuong_hieu=br.id)
        """

    def _group_by(self):
        return """
            GROUP BY
                s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
                s.user_id, s.company_id, s.sale_journal,
                s.pricelist_id, s.account_move, s.create_date, s.session_id,
                l.product_id,
                pt.categ_id, pt.pos_categ_id,
                p.product_tmpl_id,
                ps.config_id, pt.thuong_hieu, l.program_name, s.customer_ranked, 
                l.boo_total_discount, l.boo_total_discount_percentage, l.price_subtotal_incl
        """

    def _where(self):
        return """
            WHERE l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._where(), self._group_by())
        )
