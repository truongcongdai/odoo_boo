# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, api, _

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    @api.model
    def match_category_mappings(self, store_category_id=None, odoo_category_id=None, domain=None, limit=1):
        if self.channel=='magento2x' and self.default_store_id:
            self = self.default_store_id
        return super(MultiChannelSale,self).match_category_mappings(store_category_id=store_category_id,odoo_category_id=odoo_category_id,domain=domain,limit=limit)

    @api.model
    def match_partner_mappings(self, store_id = None, _type='contact',domain=None, limit=1):
        if self.channel=='magento2x' and self.default_store_id:
            self = self.default_store_id
        return super(MultiChannelSale,self).match_partner_mappings(store_id=store_id,_type=_type,domain=domain,limit=limit)

    @api.model
    def match_product_mappings(self, store_product_id=None, line_variant_ids=None,
            domain=None,limit=1,**kwargs):
        map_domain = self.get_channel_domain(domain)
        if self.channel=='magento2x':
            if store_product_id and line_variant_ids=='No Variants':
                line_variant_ids = store_product_id
        return super(MultiChannelSale,self).match_product_mappings(
            store_product_id = store_product_id,
            line_variant_ids = line_variant_ids,
            domain =domain,limit =limit,**kwargs)
