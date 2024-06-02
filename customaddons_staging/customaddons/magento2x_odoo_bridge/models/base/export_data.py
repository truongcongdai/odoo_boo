# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, api

class response_object:
    def __init__(self, model_name, template_id, variant_ids, default_code, flag=True):
        if model_name == 'product.template':
            self.id = template_id 
            variants = []
            if flag:
                self.default_code = default_code
                variants = [response_object(model_name, i, False, False, False) for i in variant_ids]
            self.variants = variants

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    def export_magento2x_categories(self):
        self.ensure_one()
        odoo_obj_ids = self.match_category_mappings(
            limit=None).mapped('odoo_category_id')
        domain = [('id','not in',odoo_obj_ids)]
        obj_ids = self.env['product.category'].search(domain)
        vals =dict(
            channel_id=self.id,
            category_ids = [(6,0,obj_ids.ids)]
        )
        obj=self.env['export.categories'].create(vals)
        return obj.magento2x_export_categories()
    
    def export_magento2x(self, exp_obj, **kwargs):
        model_name = exp_obj._name
        channel_id = self
        res = channel_id.get_magento2x_sdk()
        sdk = res.get('sdk')
        if not (sdk and sdk.oauth_token):
            return None,None
        if model_name == 'product.template':
            res = self.env['export.templates'].with_context(base_operation='export').magento2x_post_products_data(sdk,exp_obj,channel_id)
            store_template_id = res.get('create_ids').get('template_id') if res.get('create_ids') else False
            store_variants_id = res.get('create_ids').get('variant_ids') if res.get('create_ids')  else False #[1] if len(res.get('create_ids')) == 2 else res.get('create_ids')
            store_default_code = res.get('create_ids').get('default_code') if res.get('create_ids')  else False

            if store_template_id and store_variants_id:
                result = True,response_object(model_name,store_template_id,store_variants_id, store_default_code)
            else:
                result = None,None
        
        if model_name == 'product.category':
               result = self.env['export.categories'].magento2x_post_categories_bulk_data(sdk,channel_id,exp_obj,"export")
        return result

    def export_magento2x_attributes(self):
        self.ensure_one()
        odoo_obj_ids = self.match_attribute_mappings(
            limit=None).mapped('odoo_attribute_id')
        domain = [('id','not in',odoo_obj_ids)]
        obj_ids = self.env['product.attribute'].search(domain)
        vals =dict(
            channel_id=self.id,
            attribute_ids = [(6,0,obj_ids.ids)]
        )
        obj=self.env['export.attributes.magento'].create(vals)
        return obj.magento2x_export_attributes()
