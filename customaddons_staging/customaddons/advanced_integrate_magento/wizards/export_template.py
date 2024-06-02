from odoo import _, api, fields, models


class ExportMagento2xProducts(models.TransientModel):
    _inherit = ['export.templates']

    @api.model
    def magento2x_get_product_data(
            self,
            _type,
            product_id,
            channel_id,
            product_links=[],
            configurable_product_options=None,
            **kwargs
    ):
        """
        Editing post data when create product to M2 following changes made from M2
        - Not posting image
        - ...
        """
        res = super(ExportMagento2xProducts, self).magento2x_get_product_data(
            _type, product_id, channel_id, product_links, configurable_product_options, **kwargs
        )
        if not res.get('data'):
            return res
        odoo_product_id = product_id.id
        if product_id._name == 'product.template' and _type == 'simple':
            odoo_product_id = product_id.product_variant_id.id
        data = res['data']
        data.pop('image', '')
        extension_attrs = {'is_in_stock': True} if product_id.detailed_type == 'product' else {}
        data['extension_attributes']['stock_item'] = extension_attrs
        if product_id.categ_id:
            if product_id.categ_id.parent_id:
                if product_id.categ_id.parent_id.channel_mapping_ids:
                    data['extension_attributes']['category_links'] = [{
                        "position": 0,
                        "category_id": str(product_id.categ_id.parent_id.channel_mapping_ids[-1].store_category_id),
                    },
                        {
                            "position": 1,
                            "category_id": str(product_id.categ_id.parent_id.channel_mapping_ids[-1].store_category_id),
                        }]
            elif product_id.categ_id.channel_mapping_ids:
                data['extension_attributes']['category_links'] = [{
                    "position": 0,
                    "category_id": str(product_id.categ_id.channel_mapping_ids[-1].store_category_id),
                }]
        # data['extension_attributes'] = extension_attrs
        if _type == 'simple':
            data['extension_attributes'].pop('configurable_product_links', '')
        data['custom_attributes'] += [
            {
                'attribute_code': 'odoo_id',
                'value': str(odoo_product_id)
            },
            # {
            #     "attribute_code": "description",
            #     "value": product_id.description
            # },
            {
                "attribute_code": "boo_product_code",
                "value": product_id.ma_san_pham
            },
            {
                "attribute_code": "boo_brand",
                "value": product_id.thuong_hieu.name
            },
            {
                "attribute_code": "boo_season",
                "value": product_id.season.name if product_id.season else False
            },
            {
                "attribute_code": "boo_kind_of_product",
                "value": product_id.chung_loai.name if product_id.chung_loai else False
            },
            # {
            #     "attribute_code": "boo_size",
            #     "value": product_id.kich_thuoc
            # },
            {
                "attribute_code": "boo_gender",
                "value": product_id.gioi_tinh,
            },
            {
                "attribute_code": "boo_unit",
                "value": product_id.uom_name
            },
            # {
            #     "attribute_code": "boo_color",
            #     "value": product_id.mau_sac
            # },
            {
                "attribute_code": "boo_parent_group",
                "value": product_id.categ_id.parent_id.name if product_id.categ_id.parent_id else False
            },
            {
                "attribute_code": "boo_series_product",
                "value": product_id.dong_hang.name
            },
            {
                "attribute_code": "boo_provider",
                "value": "BOO"
            },
            {
                "attribute_code": "boo_gallery",
                "value": product_id.bo_suu_tap.name if product_id.bo_suu_tap else False
            },
            {
                "attribute_code": "boo_grading",
                "value": "Good"
            },
            {
                "attribute_code": "boo_material",
                "value": product_id.ma_vat_tu if _type == 'simple' and product_id.is_product_variant and product_id.ma_vat_tu else False
            },
            {
                "attribute_code": "boo_copyright",
                "value": "Undefined"
            },
            {
                "attribute_code": "boo_trending",
                "value": "Undefined"
            },
            {
                "attribute_code": "boo_feature",
                "value": "Undefined"
            },
            {
                "attribute_code": "boo_child_group",
                "value": product_id.categ_id.name if product_id.categ_id.name else False
            },
            {
                "attribute_code": "boo_concept",
                "value": "Undefined"
            },
        ]
        return res
