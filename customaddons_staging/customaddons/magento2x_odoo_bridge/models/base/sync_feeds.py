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
    def sync_magento2x_item(self, mapping, product_qty, sdk):
        result = {'data': {}, 'message': ''}
        store_id, sku = mapping.store_product_id, mapping.default_code 
        item = sdk.get_products(sku)
        product_data = item.get('data') or dict()
        qty_available = int(product_data.get('extension_attributes', {}).get('stock_item', {}).get('qty', 0))
        if qty_available:
            qty_available += product_qty
        if qty_available:
            data=dict(
                sku = mapping.default_code,
                extension_attributes=dict(
                    stock_item=dict(
                       qty= qty_available,
                       is_in_stock= qty_available >0 and 1 or 0,
                    )
                ),
            )
            res=sdk.post_products(data,sku=mapping.default_code)
            result.update(res)
        return result

    @api.model
    def sync_quantity_magento2x(self,mapping,product_qty):
        sdk = self.get_magento2x_sdk().get('sdk')
        result = {'data': {}, 'message': ''}
        sku = mapping.default_code
        item = sdk.get_products(sku)
        product_data = item.get('data') or dict()
        qty_available = 0
        extension_attributes = product_data.get('extension_attributes')
        if extension_attributes and extension_attributes.get('stock_item').get('qty') >= -999:
            # qty_available = int(extension_attributes.get('stock_item').get('qty'))
            qty_available += product_qty
        if qty_available:
            data=dict(
                sku = mapping.default_code,
                extension_attributes=dict(
                    stock_item=dict(
                       qty= qty_available,
                       is_in_stock= qty_available >0 and 1 or 0,
                    )
                ),
            )
            res=sdk.post_products(data,sku=mapping.default_code)
            result.update(res)           
        if result.get('message'):
            return False
        return True
