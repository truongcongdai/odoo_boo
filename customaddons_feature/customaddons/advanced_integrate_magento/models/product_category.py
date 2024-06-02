from odoo import models, api
import re

class ProductCategoryInherit(models.Model):
    _inherit = 'product.category'

    @api.model
    def create(self, vals_list):
        result = super(ProductCategoryInherit, self).create(vals_list)
        magento_sale_channel = self.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
        if magento_sale_channel:
            # magento_sale_channel.export_magento2x_categories()
            res = magento_sale_channel.get_magento2x_sdk()
            sdk = res.get('sdk')
            new_operation = self.env['export.categories'].sudo().create({
                'operation': 'export',
                'channel_id': magento_sale_channel.id
            })
            new_operation.magento2x_post_categories_data(sdk, magento_sale_channel, result)
        return result
    def write(self, vals):
        res = super(ProductCategoryInherit, self).write(vals)
        if 'name' in vals:
            magento_sale_channel = self.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
            if magento_sale_channel:
                res = magento_sale_channel.get_magento2x_sdk()
                sdk = res.get('sdk')
                new_operation = self.env['export.categories'].sudo().create({
                    'operation': 'update',
                    'channel_id': magento_sale_channel.id
                })
                new_operation.magento2x_post_categories_data(sdk, magento_sale_channel, self)
        return res

    def _remove_vn_char(self, text):
        patterns = {
            '[àáảãạăắằẵặẳâầấậẫẩ]': 'a',
            '[đ]': 'd',
            '[èéẻẽẹêềếểễệ]': 'e',
            '[ìíỉĩị]': 'i',
            '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
            '[ùúủũụưừứửữự]': 'u',
            '[ỳýỷỹỵ]': 'y'
        }
        output = text
        output = output.lower()
        for regex, replace in patterns.items():
            # xoa tieng viet
            output = re.sub(regex, replace, output)
            # deal with upper case
        return output

    def get_category_url(self):
        result = self.name
        result = result.strip()
        result = result.replace(' / ', '-')
        result = result.replace(' ', '-')
        result = self._remove_vn_char(result)
        return result
