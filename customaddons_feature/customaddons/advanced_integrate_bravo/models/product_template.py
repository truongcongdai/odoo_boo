from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = ['product.template']
    parent_code = fields.Char(
        string='Mã sản phẩm cha')
    bravo_system_id = fields.Char(
        string='Bravo System ID'
    )
    chat_lieu = fields.Many2one('s.product.material', string="Chất liệu")
    _sql_constraints = [
        (
            'bravo_system_id_uniq',
            'UNIQUE(bravo_system_id)',
            'Bravo ID should be unique'
        )
    ]
    def _merge_product_bravo(self):
        product_template_bravo_ids = self.env['product.template'].sudo().search(
            [('bravo_system_id', '!=', False), ('id', 'in', self.ids)])
        for product in product_template_bravo_ids:
            if len(product.product_variant_ids) > 0:
                for variant in product.product_variant_ids:
                    if len(variant.product_template_attribute_value_ids) > 0 and variant.bravo_system_child_id:
                        attribute_value_ids = variant.product_template_attribute_value_ids.mapped(
                            'product_attribute_value_id').ids
                        if len(attribute_value_ids) > 0:
                            variant_dup = product.product_variant_ids.filtered(
                                lambda v: v.product_template_attribute_value_ids.mapped(
                                    'product_attribute_value_id').ids == attribute_value_ids and v.id != variant.id and not v.bravo_system_child_id)
                            if len(variant_dup) == 1:
                                # product_variant_combination_id cua san pham bravo
                                product_variant_combination_ids = self._cr.execute("""select product_template_attribute_value_id from product_variant_combination where product_product_id = %s;""",(variant.id,))
                                # id product origin
                                ids = self._cr.fetchall()
                                bravo_product_variant_combination_ids = [r[0] for r in ids]
                                # change id product org -> product bravo
                                query_update_product_bravo_id = self._cr.execute("""Update product_variant_combination set product_product_id = %s where product_product_id = %s;""",(variant.id, variant_dup.id,))
                                # change id product org <- product bravo
                                query_update_product_org_id = self._cr.execute("""delete from product_variant_combination where product_template_attribute_value_id in %s;""",(tuple(bravo_product_variant_combination_ids),))

    def recompute_brand_odoo_bravo(self):
        for rec in self:
            s_thuong_hieu = False
            s_dong_hang = False
            s_ma_cu = False
            if rec.thuong_hieu.name:
                s_thuong_hieu = rec.thuong_hieu.name
            if rec.dong_hang.name:
                s_dong_hang = rec.dong_hang.name
            if rec.ma_cu:
                s_ma_cu = rec.ma_cu[0]
            mapping_product_line_none = self.env['s.product.brand.bravo.mapping'].sudo().search([
                ('s_bravo_brand', '=', s_thuong_hieu),
                ('s_bravo_lines', '=', False),
                ('s_first_character', '=', s_ma_cu),
            ], limit=1)
            if mapping_product_line_none:
                odoo_brand_id = mapping_product_line_none.s_odoo_brand.id
                if odoo_brand_id:
                    self._cr.execute(
                        """UPDATE product_template SET thuong_hieu=%s WHERE id = %s""",
                        (odoo_brand_id, rec.id,))
            else:
                mapping_bravo_brand = self.env['s.product.brand.bravo.mapping'].sudo().search([
                    ('s_bravo_brand', '=', s_thuong_hieu),
                    ('s_bravo_lines', '=', s_dong_hang),
                    ('s_first_character', '=', s_ma_cu),
                ], limit=1)
                if mapping_bravo_brand:
                    odoo_brand = mapping_bravo_brand.s_odoo_brand.id
                    if odoo_brand:
                        self._cr.execute(
                            """UPDATE product_template SET thuong_hieu=%s WHERE id = %s""",
                            (odoo_brand, rec.id,))
