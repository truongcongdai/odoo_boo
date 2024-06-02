from odoo import fields, models, api


class OrderLineData(models.TransientModel):
    _name = 'order.line.data.report'

    product_id = fields.Many2one('product.product', string='Sản phẩm')
    # list_price = fields.Float(string='Giá thông tin sản phẩm', related="pos_order_line_rp_id.s_lst_price")
    list_price = fields.Float(string='Giá thông tin sản phẩm', compute="_compute_list_price")
    special_price = fields.Float(string='Giá trong bảng giá')
    partner_order_id = fields.Many2one('res.partner', string='Khách hàng')
    phone = fields.Char(string='Số điện thoại', related='partner_order_id.phone',
                        groups="advanced_sale.s_boo_group_administration,advanced_sale.s_boo_group_ecom,advanced_sale.s_boo_group_area_manager,advanced_sale.s_boo_group_hang_hoa,advanced_sale.s_boo_group_dieu_phoi,advanced_sale.s_boo_group_ke_toan")
    sku = fields.Char(related='product_id.default_code')
    product_qty = fields.Float(string="Số lượng")
    boo_total_discount = fields.Float(string="Chiết khấu trực tiếp trên sản phẩm")
    boo_total_discount_percentage = fields.Float(string="Chiết khấu đơn hàng phân bổ")
    product_uom = fields.Many2one('uom.uom', string='Đơn vị đo', related="product_id.uom_id")
    price_total = fields.Float(string="Thành tiền", compute="_compute_price_total", store=True)
    boo_phan_bo_price_total = fields.Float(string="Phân bổ thành tiền")
    category_id = fields.Many2one('product.category', 'Nhóm sản phẩm', related='product_id.categ_id', store=True)
    order_code = fields.Char(string="Mã đơn hàng")
    sale_person = fields.Char(string="Nhân viên bán hàng")
    thuong_hieu = fields.Many2one('s.product.brand', string="Thương hiệu", related='product_id.thuong_hieu', store=True)
    order_type = fields.Selection(
        [('online', 'Đơn Online'), ('offline', 'Đơn tại POS'), ('ban_buon', 'Đơn bán buôn'), ('don_hang', 'Đơn hàng')],
        string='Loại đơn hàng')
    qty_delivered = fields.Float(string="Số lượng đã giao")
    sale_order_line_id = fields.Many2one('sale.order.line')
    pos_order_line_rp_id = fields.Many2one('pos.order.line')
    # pos_name = fields.Char('Cửa hàng', related='pos_order_line_rp_id.order_id.config_id.name')
    pos_name = fields.Char('Điểm bán hàng', compute="_compute_order_line_rp_id", store=True)
    order_line_create_date = fields.Datetime()
    parent_code = fields.Char(string="Mã cha", related='product_id.ma_san_pham')
    ma_cu = fields.Char(string="Mã cũ", related='product_id.ma_cu')
    ma_vat_tu = fields.Char(string="Mã vật tư", related='product_id.ma_vat_tu')
    barcode = fields.Char(string="Mã vạch", related='product_id.barcode')
    is_product_green = fields.Boolean(string="Sản phẩm xanh", related='product_id.is_product_green')
    shipping_code = fields.Char(string="Mã vận đơn", related="sale_order_line_id.shipping_code")
    mau_sac = fields.Char(related='product_id.mau_sac', store=True)
    kich_thuoc = fields.Char(related='product_id.kich_thuoc', store=True)
    pos_ref = fields.Char('Số biên lai')
    completed_date = fields.Datetime('Ngày hoàn thành', compute='_compute_complete_date')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(OrderLineData, self).fields_get(allfields, attributes)
        hide_list = ['partner_order_id']
        user = self.env.user
        user_group_has_access = [user.has_group('advanced_sale.s_boo_group_administration'),
                                 user.has_group('advanced_sale.s_boo_group_area_manager'),
                                 user.has_group('advanced_sale.s_boo_group_ecom')]
        user_group_thu_ngan = user.has_group('advanced_sale.s_boo_group_thu_ngan')
        if user_group_thu_ngan and not any(user_group_has_access):
            for field in hide_list:
                if res.get(field):
                    res[field]['exportable'] = False
        return res

    def _compute_list_price(self):
        for r in self:
            r.list_price = 0
            if r.pos_order_line_rp_id:
                r.list_price = r.pos_order_line_rp_id.s_lst_price
            elif r.sale_order_line_id:
                r.list_price = r.sale_order_line_id.s_lst_price

    @api.depends('product_id.lst_price', 'boo_total_discount_percentage', 'boo_total_discount')
    def _compute_price_total(self):
        for r in self:
            amount = 0
            discount_amount = 0
            if r.product_id.sale_ok:
                if r.pos_order_line_rp_id:
                    if 0 < r.pos_order_line_rp_id.price_unit < r.pos_order_line_rp_id.s_lst_price:
                        amount += r.pos_order_line_rp_id.qty * r.pos_order_line_rp_id.s_lst_price
                    else:
                        amount += r.pos_order_line_rp_id.qty * r.pos_order_line_rp_id.price_unit
                    if r.pos_order_line_rp_id.qty < 0:
                        discount_amount += (r.pos_order_line_rp_id.boo_total_discount_percentage + r.pos_order_line_rp_id.boo_total_discount)
                    else:
                        discount_amount += r.pos_order_line_rp_id.boo_total_discount_percentage + r.pos_order_line_rp_id.boo_total_discount
                elif r.sale_order_line_id:
                    if 0 < r.sale_order_line_id.price_unit < r.sale_order_line_id.s_lst_price:
                        amount += r.sale_order_line_id.product_uom_qty * r.sale_order_line_id.s_lst_price
                    else:
                        amount += r.sale_order_line_id.product_uom_qty * r.sale_order_line_id.price_unit
                    if r.sale_order_line_id.product_uom_qty < 0:
                        discount_amount += (r.sale_order_line_id.boo_total_discount_percentage + r.sale_order_line_id.boo_total_discount)
                    else:
                        discount_amount += r.sale_order_line_id.boo_total_discount_percentage + r.sale_order_line_id.boo_total_discount
            r.price_total = amount - discount_amount

    @api.depends('sale_order_line_id')
    def _compute_complete_date(self):
        for rec in self:
            rec.completed_date = ''
            if rec.sale_order_line_id.order_id.completed_date:
                rec.completed_date = rec.sale_order_line_id.order_id.completed_date
            if rec.pos_order_line_rp_id.order_id.date_order:
                rec.completed_date = rec.pos_order_line_rp_id.order_id.date_order

    # @api.depends('sale_order_line_id')
    # def _compute_complete_date(self):
    #     for rec in self:
    #         rec.completed_date = None
    #         if rec.pos_order_line_rp_id.order_id.picking_ids and len(
    #                 rec.pos_order_line_rp_id.order_id.picking_ids.filtered(lambda sp: sp.state == 'done')) == len(
    #                 rec.pos_order_line_rp_id.order_id.picking_ids):
    #             list_date_done = rec.pos_order_line_rp_id.order_id.picking_ids.filtered(
    #                 lambda p: p.date_done is not False).mapped('date_done')
    #             if list_date_done:
    #                 rec.completed_date = max(list_date_done)
    #         if rec.sale_order_line_id.order_id.picking_ids and len(
    #                 rec.sale_order_line_id.order_id.picking_ids.filtered(lambda sp: sp.state == 'done')) == len(
    #                 rec.sale_order_line_id.order_id.picking_ids):
    #             list_date_done = rec.sale_order_line_id.order_id.picking_ids.filtered(
    #                 lambda p: p.date_done is not False).mapped('date_done')
    #             if list_date_done:
    #                 rec.completed_date = max(list_date_done)

    @api.depends('sale_order_line_id')
    def _compute_order_line_rp_id(self):
        for rec in self:
            rec.pos_name = ''
            # location_name = ''
            if rec.pos_order_line_rp_id.order_id:
                if rec.pos_order_line_rp_id.order_id.config_id:
                    if rec.pos_order_line_rp_id.order_id.config_id.name:
                        rec.pos_name = rec.pos_order_line_rp_id.order_id.config_id.name
            if rec.sale_order_line_id.order_id:
                order_id = rec.sale_order_line_id.order_id
                if order_id.is_magento_order == True:
                    rec.pos_name = 'Online'
                else:
                    if order_id.picking_ids:
                        for picking in order_id.picking_ids:
                            move_ids = picking.move_ids_without_package.filtered(
                                lambda p: p.product_id.id == rec.product_id.id)
                            if move_ids:
                                rec.pos_name = picking.location_id.name
                # if order:
                #     vals.update({
                #         'partner_order_id': order.partner_id.id})
                #     if order.is_magento_order:
                #         vals.update({
                #             'pos_name': 'Online'})
                #     else:
                #         if order.picking_ids:
                #             for picking in order.picking_ids:
                #                 move_ids = picking.move_ids_without_package.filtered(
                #                     lambda p: p.product_id.id == line.product_id.id)
                #                 if move_ids:
                #                     vals.update({
                #                         'pos_name': picking.location_id.name})
                # stock_picking = self.env['stock.picking'].search([('sale_id', '=', rec.sale_order_line_id.order_id.id)])
                # if stock_picking:
                #     for r in stock_picking:
                #         if r.location_id:
                #             location_name += r.location_id.name + ','
                #     rec.pos_name = location_name.rstrip(',')
