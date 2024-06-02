from odoo import fields, models, api
from odoo.exceptions import ValidationError
import time


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    # todo DISABLE PRODUCT TEMPLATE NAME TRANSLATE
    name = fields.Char('Name', index=True, required=True, translate=False, track_visibility='always')

    thuong_hieu = fields.Many2one('s.product.brand', string="Thương hiệu", track_visibility='always')
    dong_hang = fields.Many2one('dong.hang', string="Dòng hàng", track_visibility='always')
    season = fields.Many2one('s.product.season', string="Mùa", track_visibility='always')
    chung_loai = fields.Many2one('s.product.species', string="Chủng loại", track_visibility='always')
    item_code = fields.Char(string="Item Code", track_visibility='always')
    # ma_vat_tu = fields.Char(string="Mã vật tư")
    ma_cu = fields.Char(string="Mã cũ", track_visibility='always')
    sku = fields.Char(string="SKU data dev", related='default_code', track_visibility='always')
    list_price = fields.Float('Sales Price', default=1.0, digits='Product Price',
                              help="Price at which the product is sold to customers.", track_visibility='always')
    # bo_suu_tap = fields.Char(string="Bộ sưu tập")
    bo_suu_tap = fields.Many2one('s.product.collection', string="Bộ sưu tập", track_visibility='always')
    mau_sac = fields.Char(string="Màu sắc", track_visibility='always')
    kich_thuoc = fields.Char(string="Kích thước", track_visibility='always')
    gioi_tinh = fields.Selection([('male', 'Male'), ('female', 'Female'), ('unisex', 'Unisex'),('other','Other')], string='Giới tính', default="other", track_visibility='always')
    gender = fields.Many2one('s.product.gender', string='Giới tính')
    ma_san_pham = fields.Char(string="Mã sản phẩm", track_visibility='always')
    is_product_green = fields.Boolean(string='Product green', default=False, track_visibility='always')
    check_sync_product = fields.Boolean(string="Đồng bộ sản phẩm", copy=False, track_visibility='always', compute='_compute_product_sale_ok', store=True)
    default_code = fields.Char('SKU', index=True, track_visibility='always')
    chat_lieu = fields.Many2one('s.product.material', string="Chất liệu", track_visibility='always')
    categ_id = fields.Many2one('product.category', track_visibility='always')
    detailed_type = fields.Selection(track_visibility='always')
    invoice_policy = fields.Selection(track_visibility='always')
    company_id = fields.Many2one('res.company', track_visibility='always')
    uom_id = fields.Many2one('uom.uom', track_visibility='always')
    uom_po_id = fields.Many2one('uom.uom', track_visibility='always')
    wk_length = fields.Float(track_visibility='always')
    width = fields.Float(track_visibility='always')
    height = fields.Float(track_visibility='always')
    dimensions_uom_id = fields.Many2one('uom.uom', track_visibility='always')
    wk_product_id_type = fields.Selection(
        selection=[
            ('wk_upc', 'UPC'),
            ('wk_ean', 'EAN'),
            ('wk_isbn', 'ISBN'),
        ], string='Product ID Type', default='wk_upc', track_visibility='always')
    s_categ_name = fields.Char(string='Nhóm sản phẩm', compute='_compute_get_categ_id', track_visibility='always')
    s_qty_available = fields.Float(string='Số lượng thực tế filter', compute='_compute_qty_available_to_filter', store=True)
    s_virtual_available = fields.Float(string='Số lượng dự báo filter', store=True)
    # tic_category_id = fields.Many2one('product.tic.category', track_visibility='always')

    @api.depends('sale_ok')
    def _compute_product_sale_ok(self):
        for r in self:
            if not r.sale_ok and r.check_sync_product:
                r.check_sync_product = False
                if r.product_variant_ids:
                    for product_variant_id in r.product_variant_ids:
                        product_variant_id.check_sync_product = False

    @api.depends('qty_available', 'virtual_available')
    def _compute_qty_available_to_filter(self):
        for res in self:
            res.sudo().write({
                's_qty_available': res.qty_available,
                's_virtual_available': res.virtual_available
            })

    def _compute_quantities(self):
        res = super(ProductTemplateInherit, self)._compute_quantities()
        products = self.filtered(lambda p: p.type != 'service')
        get_quantities = products._compute_quantities_dict()
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

    @api.depends('categ_id')
    def _compute_get_categ_id(self):
        for rec in self:
            if rec.categ_id:
                rec.s_categ_name = rec.categ_id.name

    def select_sync_push_magento(self):
        self.sync_push_magento = True

    @api.constrains('ma_san_pham')
    def check_uniq_ma_san_pham(self, parent_code=False, product_tml_id=False):
        if parent_code and product_tml_id:
            ma_san_pham = self.env['product.template'].search([('ma_san_pham', '=', parent_code)])
            tml_id = ma_san_pham.filtered(lambda r: r.id == product_tml_id)
            if len(ma_san_pham) > 0 and not tml_id:
                raise ValidationError('Mã sản phẩm đã tồn tại')
        if self.ma_san_pham:
            ma_san_pham = self.env['product.template'].search([('ma_san_pham', '=', self.ma_san_pham)])
            if len(ma_san_pham) > 1:
                raise ValidationError('Mã sản phẩm đã tồn tại')

    def action_merge_product_product(self):
        key = []
        merge_product_tmpl = []
        if len(self) <= 1:
            raise ValidationError('Merge sản phẩm thất bại. Số lượng sản phẩm chọn cần > 1')
        for records in self:
            if records.bravo_system_id:
                key.append(records)
            else:
                merge_product_tmpl.append(records)
        if len(key) == 1:
            query_product_key = self._cr.execute("""SELECT id FROM product_product WHERE product_tmpl_id = %s""",(key[0].id,))
            result_query_product_key = self._cr.dictfetchall()
            list_result_query_product_key = list(set([order['id'] for order in result_query_product_key]))
            for rec in merge_product_tmpl:
                query_merge_product_template = self._cr.execute("""Update product_product set product_tmpl_id = %s where product_tmpl_id = %s;""", (key[0].id, rec.id,))
            query_product_product_id = self._cr.execute("""SELECT id FROM product_product WHERE product_tmpl_id = %s """, (key[0].id,))
            list_result_query_product_product_id = list(set([order['id'] for order in self._cr.dictfetchall()]))
            product_id = []
            for r in list_result_query_product_product_id:
                if r not in list_result_query_product_key:
                    product_id.append(r)
            product_variant_to_add = self.env['product.product'].sudo().search([('id', 'in', product_id)])
            success = False
            if product_variant_to_add:
                for products in product_variant_to_add:
                    attribute_add = []
                    for product_value in products.product_template_attribute_value_ids.product_attribute_value_id:
                        product_value = product_value.code
                        if product_value:
                            attribute_add.append(product_value)
                    product_variant_key = self.env['product.product'].sudo().search([('id', 'in', list_result_query_product_key)])
                    if product_variant_key:
                        for variant in product_variant_key:
                            attribute_product = []
                            for variant_value in variant.product_template_attribute_value_ids.product_attribute_value_id:
                                variant_value = variant_value.code
                                if variant_value:
                                    attribute_product.append(variant_value)
                            attribute_add.sort()
                            attribute_product.sort()
                            if attribute_add == attribute_product:
                                # query_update_product_product_id = self._cr.execute("""Update product_variant_combination set product_product_id = %s where product_product_id = %s;""",(products.id,variant.id,))
                                query_delete_product_product_id = self._cr.execute("""delete from product_product where id = %s""",(variant.id,))
                                success = True
                if success == False:
                    raise ValidationError('Merge sản phẩm thất bại')
        elif len(key) < 1:
            raise ValidationError('Không có sản phẩm chính bravo')
        else:
            raise ValidationError('Không xác định sản phẩm chính bravo để merge')

    def message_track(self, tracked_fields, initial_values):
        try:
            if self._name in ['product.product', 'product.template']:
                tracking_fields = []
                if self._name == 'product.product':
                    fields = ['name', 'detailed_type', 'invoice_policy', 'uom_id', 'uom_po_id', 'list_price',
                              'tic_category_id', 'standard_price', 'default_code', 'ma_vat_tu', 'barcode',
                              'wk_product_id_type', 'categ_id', 'company_id', 'wk_length', 'width', 'height',
                              'dimensions_uom_id', 'property_account_expense_id']
                else:
                    fields = ['name', 'detailed_type', 'ma_san_pham', 'thuong_hieu', 'dong_hang', 'season', 'chat_lieu',
                              'invoice_policy', 'uom_id', 'uom_po_id', 'list_price', 'tic_category_id', 'standard_price',
                              'categ_id', 'default_code', 'chung_loai', 'ma_cu', 'bo_suu_tap', 'barcode',
                              'wk_product_id_type', 'mau_sac', 'kich_thuoc', 'gioi_tinh', 'company_id', 'wk_length',
                              'width', 'height', 'dimensions_uom_id', 'property_account_expense_id']
                tracking_fields.extend(fields)
                for field in tracking_fields:
                    if field not in tracked_fields:
                        tracked_fields.add(field)
                        if self._fields[field].type in ['many2many','many2one','one2many']:
                            for product_id in self.mapped('id'):
                                initial_values[product_id].update({
                                    field: self.mapped(field)
                                })
                        else:
                            for product_id in self.mapped('id'):
                                initial_values[product_id].update({
                                    field: self.browse(product_id).mapped(field)[0]
                                })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Tracking product field',
                'type': 'server',
                'dbname': 'boo',
                'level': 'Error',
                'path': 'url',
                'message': str(e),
                'func': 'create_product',
                'line': '0',
            })

        return super(ProductTemplateInherit, self).message_track(tracked_fields, initial_values)