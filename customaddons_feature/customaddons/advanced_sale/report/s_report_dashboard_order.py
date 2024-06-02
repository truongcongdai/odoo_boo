from odoo import tools
from odoo import api, fields, models


class SReportDashboardOrder(models.Model):
    _name = "s.report.dashboard.order"
    _auto = False
    _rec_name = 'pos_date'
    _order = 'pos_date desc'

    # pos_id = fields.Integer(string='Order ID', readonly=True)
    pos_date = fields.Datetime(string='Order Date', readonly=True)

    pos_order_id = fields.Many2one('pos.order', string='Pos Order', readonly=True)
    sale_order_id_dashboard = fields.Many2one('sale.order', string='Sale Order', readonly=True)

    pos_partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    pos_product_id = fields.Many2one('product.product', string='Product', readonly=True)
    # pos_product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    pos_state = fields.Selection(
        [('draft', 'New'), ('paid', 'Paid'), ('done', 'Posted'),
         ('invoiced', 'Invoiced'), ('cancel', 'Cancelled')],
        string='Status')
    pos_user_id = fields.Many2one('res.users', string='User', readonly=True)
    # pos_price_total = fields.Float(string='Total Price', readonly=True)
    pos_price_sub_total = fields.Float(string='Subtotal w/o discount', readonly=True)
    # pos_total_discount = fields.Float(string='Total Discount', readonly=True)
    # pos_average_price = fields.Float(string='Average Price', readonly=True, group_operator="avg")
    pos_company_id = fields.Many2one('res.company', string='Company', readonly=True)
    pos_nbr_lines = fields.Integer(string='Sale Line Count', readonly=True)
    # pos_product_qty = fields.Integer(string='Product Quantity', readonly=True)
    # pos_journal_id = fields.Many2one('account.journal', string='Journal')
    # pos_delay_validation = fields.Integer(string='Delay Validation')
    # pos_invoiced = fields.Boolean(readonly=True)
    # pos_config_id = fields.Many2one('pos.config', string='Point of Sale', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    # pos_pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', readonly=True)
    # pos_session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    # pos_margin = fields.Float(string='Margin', readonly=True)
    pos_source_id = fields.Many2one('utm.source', 'Source')
    pos_reference = fields.Char('Order Reference', readonly=True)
    pos_customer_ranked = fields.Char(string='Hạng', readonly=True)
    pos_name = fields.Char(string='Điểm bán hàng', readonly=True)
    pos_team_id = fields.Many2one('crm.team', string="Sales Team")

    #####
    thuong_hieu_name = fields.Many2one(
        's.product.brand',
        string='Thương hiệu',
    )
    kich_thuoc_sp = fields.Char(
        string='Kích thước'
    )
    don_doi_tra = fields.Boolean(
        string='Đơn đổi trả'
    )
    quoc_gia_khach_hang = fields.Many2one('res.country', string='Quốc gia khách hàng', ondelete='restrict')
    don_ban_buon = fields.Boolean(
        string='Đơn bán buôn'
    )
    mau_sac_sp = fields.Char(
        string='Màu sắc'
    )
    coupon_program_name = fields.Char(string='CTKM')
    count_don_km = fields.Integer(string='Tổng khuyến mãi áp dụng')
    # coupon_program_name = fields.Char(string='Hạng', store=True)
    # doanh_thu = fields.Float(
    #     string='Doanh thu'
    # )
    tong_chiet_khau = fields.Float(
        string='Tổng chiết khấu phân bổ và trực tiếp'
    )
    tong_doanh_so = fields.Float(
        string='Tổng doanh số'
    )
    tong_doanh_so_chua_thue = fields.Float(
        string='Tổng doanh số chưa thuế'
    )
    doanh_thu_chuan = fields.Float(
        string='Doanh thu (Tổng doanh thu - chiết khấu phân bổ)'
    )
    # tracking = fields.Float(
    #     string='Tracking'
    # )
    so_luong_san_pham = fields.Integer(
        string='Số lượng sản phẩm'
    )
    date_order_pos_filter = fields.Datetime(string="Date filter")
    tinh_trang_don_hang =fields.Selection([
        ('moi', 'Mới'),
        ('hoan_thanh', 'Hoàn thành'),
        ('da_huy', 'Đã hủy'),
    ], string='Tình trạng đơn hàng')

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(SReportDashboardOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     self.init()
    #     return res

    def _select(self):
        return """
                SELECT
                    MIN(l.id) AS id,
                    COUNT(*) AS pos_nbr_lines,
                    pos.date_order AS pos_date,
                    SUM(l.qty) AS pos_product_qty,
                    SUM(l.qty * l.price_unit / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS pos_price_sub_total,
                    SUM(ROUND((l.qty * l.price_unit) * (100 - l.discount) / 100 / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END, cu.decimal_places)) AS pos_price_total,
                    SUM((l.qty * l.price_unit) * (l.discount / 100) / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS pos_total_discount,
                    CASE
                        WHEN SUM(l.qty * u.factor) = 0 THEN NULL
                        ELSE (SUM(l.qty*l.price_unit / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END)/SUM(l.qty * u.factor))::decimal
                    END AS pos_average_price,
                    SUM(cast(to_char(date_trunc('day',pos.date_order) - date_trunc('day',pos.create_date),'DD') AS INT)) AS pos_delay_validation,
                    
                    pos.id as pos_order_id,
                    pos.name as pos_name,
                    pos.sale_order_id_dashboard as sale_order_id_dashboard,
                    
                    pos.partner_id AS pos_partner_id,
                    pos.pos_order_status AS tinh_trang_don_hang,

                    pos.source_id AS pos_source_id,
                    pos.pos_reference AS pos_reference,
                    pos.crm_team_id AS pos_team_id,
                    p.kich_thuoc AS kich_thuoc_sp,
                    pos.is_refund_order AS don_doi_tra,
                    False AS don_ban_buon,
                    partner.country_id AS quoc_gia_khach_hang,
                    p.mau_sac AS mau_sac_sp,
                    pos.state AS pos_state,
                    pos.user_id AS pos_user_id,
                    pos.company_id AS pos_company_id,
                    pos.sale_journal AS pos_journal_id,
                    l.product_id AS pos_product_id,
                    p.product_tmpl_id,
                    ps.config_id,
                    
                    pt.categ_id AS product_categ_id,
                    
                    pos.pricelist_id,
                    pos.session_id,
                    pos.account_move IS NOT NULL AS pos_invoiced,
                    SUM(l.price_subtotal - l.total_cost / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS pos_margin, 
                    pt.thuong_hieu AS thuong_hieu_name,
                    pos.date_order_pos_filter AS date_order_pos_filter,
                    pos.customer_ranked AS pos_customer_ranked,
                    SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL THEN boo_total_discount +l.boo_total_discount_percentage ELSE 0 END) AS tong_chiet_khau,
                    
                    SUM(l.price_subtotal_incl) + SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL THEN boo_total_discount +l.boo_total_discount_percentage ELSE 0 END) AS tong_doanh_so,
                    
                    SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL THEN abs(l.qty) ELSE 0 END ) AS so_luong_san_pham,
                    
                    SUM(l.price_subtotal_incl) AS doanh_thu_chuan,
                             
                    SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price > l.price_unit AND l.price_unit !=0 THEN l.qty*l.s_lst_price 
                             WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL AND l.s_lst_price <= l.price_unit THEN l.qty*l.price_unit 
                             ELSE 0 END) - SUM(CASE WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND l.boo_total_discount_percentage != 0 THEN l.price_subtotal_incl - l.boo_total_discount_percentage 
                             WHEN (l.program_id is not NULL OR l.gift_card_id is not NULL OR l.coupon_id is not NULL OR l.is_line_gift_card = True) AND l.boo_total_discount_percentage != 0 THEN l.boo_total_discount_percentage 
                             WHEN l.program_id is NULL AND l.gift_card_id is NULL AND l.coupon_id is NULL AND l.is_line_gift_card = False AND (l.boo_total_discount_percentage=0 or l.boo_total_discount_percentage is null or l.is_product_service=True) THEN l.price_subtotal_incl ELSE 0 END) AS tracking,
                    
                    SUM(CASE WHEN l.program_id is NULL AND l.is_line_gift_card = False AND l.coupon_id is NULL THEN l.price_subtotal 
                             ELSE 0 END) AS tong_doanh_so_chua_thue,
                             
                    l.program_name AS coupon_program_name,
                    CASE WHEN l.program_name is not NULL THEN count(pos.id)
                             ELSE 0 END AS count_don_km
                    
                                            
            """

    def _from(self):
        return """
                FROM pos_order_line AS l
                    INNER JOIN pos_order pos ON (pos.id=l.order_id)
                    join res_partner partner on pos.partner_id = partner.id
                    LEFT JOIN product_product p ON (l.product_id=p.id)
                    LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                    LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
                    LEFT JOIN pos_session ps ON (pos.session_id=ps.id)
                    LEFT JOIN res_company co ON (pos.company_id=co.id)
                    LEFT JOIN res_currency cu ON (co.currency_id=cu.id)
                    
                    LEFT JOIN s_product_brand br ON (pt.thuong_hieu=br.id)
            """

    def _group_by(self):
        return """
            GROUP BY
                pos.id, pos.date_order, pos.partner_id,pos.state, pos.pos_reference,
                pos.user_id, pos.company_id, pos.sale_journal,
                pos.pricelist_id, pos.account_move, pos.create_date, pos.session_id,
                l.product_id,pos_name,
                pt.categ_id,
                partner.country_id,
                p.product_tmpl_id,
                ps.config_id,l.order_id, p.kich_thuoc, p.mau_sac
                ,pt.thuong_hieu, l.program_name, pos.customer_ranked,l.boo_total_discount,l.boo_total_discount_percentage,l.price_subtotal_incl
        """

    def init(self):
        query_table = self._cr.execute(
            """DROP VIEW IF EXISTS s_report_dashboard_order CASCADE""",
        )
        query_table = self._cr.execute(
            """DROP VIEW IF EXISTS dashboard_sale_order_report CASCADE""",
        )
        query_table = self._cr.execute(
            """DROP VIEW IF EXISTS dashboard_pos_order_report CASCADE""",
        )
        # Create view sale_order
        self._cr.execute("""
            CREATE OR REPLACE VIEW dashboard_sale_order_report AS (
                %s
                %s
                %s
            )
        """ % (self._select_so(), self._from_so(), self._group_by_so())
        )
        # Create view pos_order
        self._cr.execute("""
            CREATE OR REPLACE VIEW dashboard_pos_order_report AS (
                %s
                %s
                %s
            )
        """ % (self._select(), self._from(), self._group_by())
         )

        self._cr.execute("""
            CREATE OR REPLACE VIEW s_report_dashboard_order AS
                (SELECT id,pos_nbr_lines,pos_date,
                        pos_price_sub_total, 
                        sale_order_id_dashboard,
                        pos_partner_id, pos_source_id, pos_state,
                        pos_user_id, pos_company_id,
                        pos_product_id,
                        product_categ_id, pricelist_id,
                        thuong_hieu_name, date_order_pos_filter,
                        pos_customer_ranked, tong_chiet_khau, tong_doanh_so,
                        so_luong_san_pham, doanh_thu_chuan,
                        pos_reference, tong_doanh_so_chua_thue, coupon_program_name,
                        count_don_km, pos_team_id, tinh_trang_don_hang,pos_name,
                        kich_thuoc_sp, mau_sac_sp, pos_order_id, don_doi_tra, quoc_gia_khach_hang, don_ban_buon
                        FROM dashboard_pos_order_report
                UNION all
                    SELECT id,nbr,date,
                      price_subtotal,
                      sale_order_id,
                      partner_id, source_id, state,
                      user_id, company_id,
                      product_id,
                      categ_id, pricelist_id,
                      thuong_hieu_id, date_order_sale_filter,
                      customer_ranked, tong_chiet_khau, gia_tong,
                      product_uom_qty, price_total,
                      name, tong_doanh_so_chua_thue, coupon_program_name,
                      count_don_km, team_id, tinh_trang_don_hang,pos_name,
                      kich_thuoc_sp, mau_sac_sp , pos_order_id_dashboard, don_doi_tra, quoc_gia_khach_hang, don_ban_buon
                      FROM dashboard_sale_order_report)
        """)

    ####sale order
    def _select_so(self):
        return """
            SELECT coalesce(min(l.id), -s.id) as id,
                l.product_id as product_id,
                t.uom_id as product_uom,
                CASE WHEN l.product_id IS NOT NULL THEN sum(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as product_uom_qty,
                CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_delivered / u.factor * u2.factor) ELSE 0 END as qty_delivered,
                CASE WHEN l.product_id IS NOT NULL THEN SUM((l.product_uom_qty - l.qty_delivered) / u.factor * u2.factor) ELSE 0 END as qty_to_deliver,
                CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_invoiced / u.factor * u2.factor) ELSE 0 END as qty_invoiced,
                CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_to_invoice / u.factor * u2.factor) ELSE 0 END as qty_to_invoice,
                CASE WHEN l.product_id IS NOT NULL AND l.order_id NOT IN (SELECT id FROM sale_order WHERE return_order_id IS NOT NULL AND 
                amount_total=0 AND return_order_id IN (SELECT id FROM sale_order WHERE is_magento_order=TRUE))
                    THEN sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_total,
                CASE WHEN l.product_id IS NOT NULL THEN sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_subtotal,
                CASE WHEN l.product_id IS NOT NULL THEN sum(l.untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_to_invoice,
                CASE WHEN l.product_id IS NOT NULL THEN sum(l.untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_invoiced,
                count(*) as nbr,
                s.name as name,
                null as pos_name,
                s.date_order as date,
                s.state as state,
                s.partner_id as partner_id,
                s.user_id as user_id,
                s.company_id as company_id,
                s.campaign_id as campaign_id,
                s.medium_id as medium_id,
                s.customer_ranked as customer_ranked,
                s.sale_order_status as tinh_trang_don_hang,
                s.source_id as source_id,
                
                s.pos_order_id_dashboard as pos_order_id_dashboard,
                
                extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                
                t.categ_id as categ_id,
                
                s.pricelist_id as pricelist_id,
                s.analytic_account_id as analytic_account_id,
                s.team_id as team_id,
                p.product_tmpl_id,
                partner.industry_id as industry_id,
                partner.commercial_partner_id as commercial_partner_id,
                CASE WHEN l.product_id IS NOT NULL THEN sum(p.weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as weight,
                CASE WHEN l.product_id IS NOT NULL THEN sum(p.volume * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as volume,
                l.discount as discount,
                CASE WHEN l.product_id IS NOT NULL THEN sum((l.price_unit * l.product_uom_qty * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END))ELSE 0 END as discount_amount,
                s.id as sale_order_id,
                t.thuong_hieu AS thuong_hieu_id,
                p.kich_thuoc AS kich_thuoc_sp,
                s.is_return_order AS don_doi_tra,
                s.is_sell_wholesale AS don_ban_buon,
                partner.country_id AS quoc_gia_khach_hang,
                p.mau_sac AS mau_sac_sp,
                s.s_promo_program_m2 AS chuong_trinh_khuyen_mai_order,
                s.date_order_sale_filter as date_order_sale_filter,
                
                CASE WHEN l.product_id IS NOT NULL AND l.order_id NOT IN (SELECT id FROM sale_order WHERE return_order_id IS NOT NULL AND amount_total=0 AND return_order_id IN (SELECT id FROM sale_order WHERE is_magento_order=TRUE))
                    THEN SUM(CASE WHEN l.program_name IS NULL AND l.gift_card_id IS NULL AND (l.is_line_coupon_program is NULL or l.is_line_coupon_program is FALSE) AND l.is_delivery is FALSE THEN boo_total_discount + l.boo_total_discount_percentage ELSE 0 END) ELSE 0 END as tong_chiet_khau,

                CASE WHEN l.product_id IS NOT NULL AND l.order_id NOT IN (SELECT id FROM sale_order WHERE return_order_id IS NOT NULL AND amount_total=0 AND return_order_id IN (SELECT id FROM sale_order WHERE is_magento_order=TRUE))
                    THEN sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) + SUM(CASE WHEN l.program_name IS NULL AND l.gift_card_id IS NULL AND (l.is_line_coupon_program is NULL or l.is_line_coupon_program is FALSE) AND l.is_delivery is FALSE THEN boo_total_discount + l.boo_total_discount_percentage ELSE 0 END)
                    ELSE 0 END as gia_tong,

                SUM(CASE WHEN l.coupon_program_id IS NULL AND l.gift_card_id is NULL AND l.is_delivery is FALSE AND l.is_product_free is FALSE AND l.is_line_coupon_program is FALSE
                 THEN l.product_uom_qty ELSE 0 END ) AS so_luong_san_pham,
                 
                SUM(CASE WHEN l.coupon_program_id is NULL AND l.gift_card_id is Null AND l.is_line_coupon_program is False AND l.s_lst_price > l.price_unit THEN l.product_uom_qty*l.s_lst_price
                         WHEN l.coupon_program_id is NULL AND l.gift_card_id is Null AND l.is_line_coupon_program is False AND l.s_lst_price <= l.price_unit THEN l.product_uom_qty*l.price_unit 
                         ELSE 0 END) AS tong_doanh_so,
                
                SUM(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) - sum(price_tax) AS tong_doanh_so_chua_thue,
                
                l.program_name AS coupon_program_name,
                CASE WHEN l.program_name is not NULL AND s.id in (select id from sale_order where id in (select order_id from sale_order_line where program_name is not NULL group by order_id)) THEN count(s.id)
                         ELSE 0 END AS count_don_km
        """

    def _from_so(self):
        return """
            FROM sale_order_line l
                right outer join sale_order s on (s.id=l.order_id)
                join res_partner partner on s.partner_id = partner.id
                left join product_product p on (l.product_id=p.id)
                left join product_template t on (p.product_tmpl_id=t.id)
                left join uom_uom u on (u.id=l.product_uom)
                left join uom_uom u2 on (u2.id=t.uom_id)
                left join product_pricelist pp on (s.pricelist_id = pp.id)
        """

    def _group_by_so(self):
        return """
            GROUP BY
                l.product_id,
                    l.order_id,
                    t.uom_id,
                    s.name,
                    s.date_order,
                    s.partner_id,
                    s.user_id,
                    s.state,
                    s.company_id,
                    s.campaign_id,
                    s.medium_id,
                    s.source_id,
                    s.pricelist_id,
                    s.analytic_account_id,
                    s.team_id,
                    p.product_tmpl_id,
                    partner.country_id,
                    partner.industry_id,
                    partner.commercial_partner_id,
                    l.discount,
                    s.id,
                    t.categ_id,
                    t.thuong_hieu, p.kich_thuoc, p.mau_sac, l.boo_total_discount, l.boo_total_discount_percentage, s.s_promo_program_m2, l.program_name
        """