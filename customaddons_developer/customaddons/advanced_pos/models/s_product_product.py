from odoo import fields, models, api
from datetime import datetime
import ast
from odoo.exceptions import ValidationError


class SProductProduct(models.Model):
    _inherits = {'product.template': 'product_tmpl_id'}
    _inherit = 'product.product'
    s_loyalty_product_reward = fields.Boolean(string='Sản phẩm quy đổi điểm')
    # thuong_hieu = fields.Many2one('s.product.brand', string="Thương hiệu")
    # dong_hang = fields.Many2one('dong.hang', string="Dòng hàng")
    # season = fields.Many2one('s.product.season', string="Mùa")
    # chung_loai = fields.Many2one('s.product.species', string="Chủng loại")
    # item_code = fields.Char(string="Item Code", required=True)
    ma_vat_tu = fields.Char(string="Mã vật tư", track_visibility='always')
    # ma_cu = fields.Char(string="Mã cũ")
    # sku = fields.Char(string="SKU data dev", related='default_code', track_visibility='always')
    # list_price = fields.Float('Sales Price', default=1.0, digits='Product Price',
    #                           help="Price at which the product is sold to customers.", track_visibility='always')
    # bo_suu_tap = fields.Char(string="Bộ sưu tập")
    mau_sac = fields.Char(string="Màu sắc", compute='_compute_variants_attribute', store=True, track_visibility='always')
    kich_thuoc = fields.Char(string="Kích thước", compute='_compute_variants_attribute', store=True, track_visibility='always')
    # ma_size = fields.Char(string="Mã Size", compute='_compute_ma_size', store=True)
    # gioi_tinh = fields.Selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')], string='Giới tính')
    # ma_san_pham = fields.Char(string="Mã sản phẩm")
    # is_product_green = fields.Boolean(string='Product green', default=False)
    coupon_ids = fields.Many2many(
        comodel_name='s.product.coupon.program',
        compute="_compute_s_related_coupon"
    )
    default_code = fields.Char('SKU', index=True, track_visibility='always')
    barcode = fields.Char(track_visibility='always')
    standard_price = fields.Float(track_visibility='always')
    from_coupon_program = fields.One2many('coupon.program', 'discount_line_product_id')
    lst_price = fields.Float(tracking=True)
    s_free_product_id = fields.Integer(
        string='S_free_product_id', help="id của sản phẩm được tặng (mục đích phục vụ cho CTKM tặng nhiều sản phẩm).")
    is_gift_free_product = fields.Boolean(string='is_gift_free_product', default=False)
    # name = fields.Char(track_visibility='always')
    # tic_category_id = fields.Many2one('product.tic.category', track_visibility='always')
    # categ_id = fields.Many2one('product.category', track_visibility='always')
    # company_id = fields.Many2one('res.company', track_visibility='always')
    s_note = fields.Char(string='Ghi chú sản phẩm biến thể', track_visibility='always')
    s_product_expiration_time = fields.Integer(string='Thời gian quá hạn của sản phẩm')
    is_gift_product = fields.Boolean(string="Là sản phẩm quà tặng", default=False)
    s_qty_available = fields.Float(string='Số lượng thực tế filter', store=True)
    s_virtual_available = fields.Float(string='Số lượng dự báo filter', store=True)

    def _compute_quantities(self):
        res = super(SProductProduct, self)._compute_quantities()
        products = self.filtered(lambda p: p.type != 'service')
        get_quantities = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'),
                                                           self._context.get('package_id'),
                                                           self._context.get('from_date'), self._context.get('to_date'))
        for product in products:
            if product.s_qty_available != get_quantities[product.id]['qty_available']:
                product.sudo().write({
                    's_qty_available': get_quantities[product.id]['qty_available']
                })
            if product.s_virtual_available != get_quantities[product.id]['virtual_available']:
                product.sudo().write({
                    's_virtual_available': get_quantities[product.id]['virtual_available']
                })
        return res

    @api.constrains('default_code')
    def check_default_code(self):
        self.ensure_one()
        if self.default_code:
            if self.env['product.product'].search_count([('default_code', '=', self.default_code)]) > 1:
                raise ValidationError('Mã SKU này đã tồn tại ở sản phẩm khác. Vui lòng thiết lập lại mã SKU.')

    def _compute_s_related_coupon(self):
        # tìm các chương trình được áp dụng cho sản phẩm
        self.env.cr.execute("DELETE FROM s_product_coupon_program WHERE product_id = %s", (self.id,))
        for rec in self:
            rec.sudo().coupon_ids = False
            update_data_list = []
            # programs = rec.env['coupon.program'].sudo().search(
            #     ['|', ('rule_date_to', '=', False), ('rule_date_to', '>=', datetime.today())],limit=1)
            promo_id = rec.env['coupon.program'].sudo().search(
                ['&', ('coupon_ids', '=', False), ('rule_date_to', '>=', datetime.today())]
            ).mapped('id')
            coupon_id = rec.env['coupon.program'].sudo().search(
                ['&', ('coupon_ids', '!=', False), ('expiration_date', '>=', fields.Date.today())]
            ).mapped('id')
            expired_promo = rec.env['coupon.program'].sudo().search(['&', ('coupon_ids', '=', False), ('rule_date_to', '=', False)]).mapped('id')
            expired_coupon = rec.env['coupon.program'].sudo().search(['&', ('coupon_ids', '!=', False), ('expiration_date', '=', False)]).mapped('id')
            programs_id = []
            programs_id.extend(promo_id)
            programs_id.extend(coupon_id)
            programs_id.extend(expired_promo)
            programs_id.extend(expired_coupon)
            programs = rec.env['coupon.program'].sudo().search([('id', 'in', programs_id)])
            if programs:
                for program in programs:
                    domain = ast.literal_eval(program.rule_products_domain) if program.rule_products_domain else []
                    domain.insert(0, ['id', '=', rec.id])
                    count = rec.env['product.product'].search_count(domain)
                    if count > 0:
                        # tìm các POS được áp dụng cho chương trình
                        pos = rec.env['pos.config'].sudo().search([('program_ids', 'in', [program.id])])
                        if pos:
                            update_data = {'coupon_id': program.id, 'pos_config_ids': [(6, 0, pos.ids)], 'product_id': self.id}
                            if program.reward_type == 'discount':
                                if program.discount_apply_on == 'specific_products':
                                    if rec.id in program.discount_specific_product_ids.mapped('id'):
                                        update_data_list.append(update_data)
                                elif program.discount_apply_on == 'cheapest_product':
                                    for pos_order in program.pos_order_ids:
                                        if rec.id in pos_order.lines.product_id.mapped('id') and rec.lst_price == min(
                                                pos_order.lines.product_id.filtered(
                                                    lambda p: p.detailed_type == 'product').mapped('lst_price')):
                                            update_data_list.append(update_data)
                                elif program.discount_apply_on == 'on_order':
                                    update_data_list.append(update_data)
                            elif program.reward_type == 'product' or program.reward_type == 'free_shipping':
                                update_data_list.append(update_data)
            rec.sudo().coupon_ids = [(5, 0, 0)]
            for val in update_data_list:
                rec.sudo().coupon_ids.create(val)

    # @api.depends('product_template_attribute_value_ids')
    # def _compute_ma_size(self):
    #     for rec in self:
    #         ma_size = ''
    #         for product_template_attribute_value in rec.product_template_attribute_value_ids:
    #             if product_template_attribute_value.attribute_id.type == "size":
    #                 ma_size = product_template_attribute_value.product_attribute_value_id.code
    #         rec.ma_size = ma_size

    def _coupon_domain(self):
        for rec in self:
            today = datetime.now()
            return ["|", ('coupon_id.rule_date_to', '=', None), ('coupon_id.rule_date_to', '>', today), "&",
                    ("coupon_id.active", "=", True), "|", "&",
                    ("coupon_id.discount_apply_on", "=", "specific_products"),
                    ("coupon_id.discount_specific_product_ids", "in", rec.id),
                    ("coupon_id.discount_apply_on", "!=", "specific_products")]

    def get_product_quantities(self, picking_type_id):
        available_quantity = 0
        if picking_type_id:
            # for rec in self.env['stock.warehouse'].search([('pos_type_id', '=', picking_type_id)], limit=1):
            #     available_quantity = self.with_context({'warehouse': rec.id}).qty_available
            picking_type = self.env['stock.picking.type'].sudo().browse(picking_type_id)
            if picking_type:
                if picking_type.default_location_src_id:
                    loc_id = picking_type.default_location_src_id.id
                    data = self.env['stock.quant'].sudo().read_group([
                        ('product_id', '=', self.id), ('location_id', '=', loc_id),
                        ('location_id.s_is_transit_location', '=', False), ('location_id.scrap_location', '=', False)
                    ], ['location_id', 'quantity', 'reserved_quantity'], ['location_id'])
                    for e in data:
                        if e['quantity'] > 0:
                            available_quantity += int(e['quantity'] - e['reserved_quantity'])
        # print(available_quantity)
        return available_quantity

    @api.depends('product_template_attribute_value_ids')
    def _compute_variants_attribute(self):
        # count = 0
        for attr in self:
            # count +=1
            # print(str(count) + '/'+str(len(self)))
            attr.kich_thuoc = False
            attr.mau_sac = False
            if attr.product_template_attribute_value_ids:
                for rec in attr.product_template_attribute_value_ids:
                    if rec.attribute_id.type == 'size':
                        attr.kich_thuoc = rec.name
                    elif rec.attribute_id.type == 'color':
                        attr.mau_sac = rec.name
