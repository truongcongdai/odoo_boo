from odoo import fields, models, api
import json

from odoo.exceptions import ValidationError
from ..controllers.bravo_api_controllers import grooming_product_data
from collections import defaultdict
from odoo.http import request


class CreateMultiProductAttributes(models.Model):
    _name = 'create.multi.product.attributes'
    _description = 'Import product'
    product_template_id = fields.Char(
        string='Sản phẩm cha')
    name = fields.Char(
        string='Tên',
        required=False)
    detailed_type = fields.Selection(
        string='Loại sản phẩm',
        selection=[
            ('consu', 'Consumable'),
            ('service', 'Service'), ('product', 'Sản phẩm lưu kho')],
        required=False, )
    sku = fields.Char(
        string='SKU',
        required=False)
    product_attribute_value_ids = fields.Many2many('product.attribute.value',
                                                   string='Mã giá trị thuộc tính')
    product_attribute_ids = fields.Many2many('product.attribute',
                                             string='Thuộc tính')
    # code = fields.Char(
    #     string='Mã giá trị thuộc tính',
    #     required=False)
    product_code = fields.Char(
        string='Mã sản phẩm',
        required=False)
    lst_price = fields.Float(
        string='List price',
        required=False)
    collection = fields.Many2one('s.product.collection', string="Bộ sưu tập")
    categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Nhóm sản phẩm')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('unisex', 'Unisex'), ('other', 'Other')],
                              string='')
    barcode = fields.Char(
        string='barcode',
        required=False)
    season = fields.Many2one('s.product.season', string="Mùa")
    product_line = fields.Many2one('dong.hang', string="Dòng hàng")
    brand_name = fields.Many2one('s.product.brand', string="Thương hiệu")
    chat_lieu = fields.Many2one('s.product.material', string="Chất liệu")
    chung_loai = fields.Many2one('s.product.species', string='Chủng loại')
    old_code = fields.Char(string="Mã cũ")
    material_code = fields.Char(string="Mã vật tư")
    product_expiration_time = fields.Integer(string='Thời gian quá hạn của sản phẩm')

    @api.constrains('sku', 'barcode')
    def _check_sku_unique(self):
        if self.sku and self.env['product.product'].search_count([('default_code', '=', self.sku)]) > 1:
            raise ValidationError('SKU đã tồn tại')
        if self.barcode and self.env['product.product'].search_count([('barcode', '=', self.barcode)]) > 1:
            raise ValidationError('Barcode đã tồn tại')

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Sản phẩm biến thể',
            'template': '/advanced_integrate_bravo/static/xlsx/template_san_pham_bien_the.xlsx'
        }]

    """ma san pham la unique"""

    def cron_multi_product_attributes(self):
        limit_import_product = self.sudo().env['ir.config_parameter'].get_param('bravo.limit_import_product_variants', 20)
        # get ma san pham exist
        query_product_code_exist = self._cr.execute(
            """SELECT ma_san_pham FROM product_template GROUP BY ma_san_pham""", )
        list_product_code_exist = [item[0] for item in self._cr.fetchall()]
        # if len(list_product_code_exist) > 0:
        # get ma san pham
        query_product_code = self._cr.execute(
            """SELECT product_code FROM create_multi_product_attributes GROUP BY product_code""", )
        list_product_code = [item[0] for item in self._cr.fetchall()]
        list_product = [p for p in list_product_code if p not in list_product_code_exist]
        list_product_exist = [p for p in list_product_code if p in list_product_code_exist]
        if list_product_exist:
            query_product_code = self._cr.execute(
                """DELETE FROM create_multi_product_attributes WHERE product_code IN %s""",
                (tuple(list_product_exist),))
        if len(list_product) > 0:
            for product_code in list_product[:limit_import_product]:
                # get san pham bien the
                query_product_attributes = self._cr.execute(
                    """SELECT id FROM create_multi_product_attributes WHERE product_code=%s""", (product_code,))
                list_product_variant = [item[0] for item in self._cr.fetchall()]
                # get gia tri san pham (product.attribute.value)
                query_attribute_value = self._cr.execute(
                    """SELECT product_attribute_value_id FROM create_multi_product_attributes_product_attribute_value_rel WHERE create_multi_product_attributes_id IN %s;""",
                    (tuple(list_product_variant),))
                list_attribute_value = list(set([item[0] for item in self._cr.fetchall()]))
                product_attribute_ids = self.env['create.multi.product.attributes'].sudo().browse(
                    list_product_variant)
                if len(list_attribute_value) > 0:
                    # get dict attribute & attribute values
                    query_attribute_ids = self._cr.execute(
                        """SELECT attribute_id,id FROM product_attribute_value WHERE id in %s""",
                        (tuple(list_attribute_value),))
                    dict_attribute_ids = self._cr.dictfetchall()
                    # filter attr & attr value {{attribute_id:[values_id]}}
                    rev_multidict = {}
                    for attr in dict_attribute_ids:
                        rev_multidict.setdefault(attr['attribute_id'], set()).add(attr['id'])
                    data = self.grooming_product_template_data(product_attribute_ids)
                    data.update({
                        'attribute_line_ids': [(0, 0, {"attribute_id": key, "value_ids": list(vals)}) for key, vals in
                                               rev_multidict.items()],
                    })
                    product_template_id = self.env['product.template'].with_env(self.env(user=data.get('create_uid'))).sudo().create(data)
                    if product_template_id:
                        for product_variant in product_template_id.product_variant_ids:
                            # filter_product_variant= product_attribute_ids.filtered(lambda a: a.product_attribute_value_ids.ids==product_variant.product_template_variant_value_ids.product_attribute_value_id.ids)
                            for attribute in product_attribute_ids:
                                if attribute.product_attribute_value_ids.ids == product_variant.product_template_attribute_value_ids.product_attribute_value_id.ids:
                                    product_variant.sudo().write({
                                        'default_code': attribute.sku,
                                        'ma_san_pham': attribute.product_code,
                                        'barcode': attribute.barcode,
                                        'ma_vat_tu': attribute.material_code,
                                        's_product_expiration_time': attribute.product_expiration_time,
                                    })
                else:
                    data = self.grooming_product_template_data(product_attribute_ids)
                    if data:
                        product_template_id = self.env['product.template'].sudo().create(data)
                product_attribute_ids.unlink()
            # list_product_remove = [p for p in list_product_code if p in list_product_code_exist]
            # if list_product_remove:
            #     self.env['create.multi.product.attributes'].sudo().browse(list_product_remove).unlink()

    def grooming_product_template_data(self, product_attribute_ids):
        if product_attribute_ids:
            vals = {
                'name': product_attribute_ids[0].product_template_id,
                'detailed_type': product_attribute_ids[0].detailed_type,
                'ma_san_pham': product_attribute_ids[0].product_code,
                'list_price': product_attribute_ids[0].lst_price,
                'bo_suu_tap': product_attribute_ids[0].collection.id if product_attribute_ids[
                    0].collection else False,
                'categ_id': product_attribute_ids[0].categ_id.id if product_attribute_ids[
                    0].categ_id else False,
                'gioi_tinh': product_attribute_ids[0].gender,
                'season': product_attribute_ids[0].season.id if product_attribute_ids[0].season else False,
                'dong_hang': product_attribute_ids[0].product_line.id if product_attribute_ids[
                    0].product_line else False,
                'thuong_hieu': product_attribute_ids[0].brand_name.id if product_attribute_ids[
                    0].brand_name else False,
                'chat_lieu': product_attribute_ids[0].chat_lieu.id if product_attribute_ids[
                    0].chat_lieu else False,
                'ma_cu': product_attribute_ids[0].old_code,
                'chung_loai': product_attribute_ids[0].chung_loai.id,
                # 'ma_vat_tu': product_attribute_ids[0].material_code,
                'sync_push_magento': True,
                'available_in_pos': True,
                'create_uid': product_attribute_ids[0].create_uid.id
            }
            return vals
