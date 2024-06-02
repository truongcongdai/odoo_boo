# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from ast import literal_eval
from odoo import models, api
from odoo.addons.magento2x_odoo_bridge.tools.magento_api import Magento2
from odoo.addons.odoo_multi_channel_sale.tools import get_hash_dict
class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    @api.model
    def get_magento2x_channel_id(self):
        return self.env['multi.channel.sale.config'].sudo().get_default_fields({}).get('default_magneto2x_channel_id')

    @api.model
    def get_magento2x_sdk(self):
        message= ''
        sdk = None
        try:
            debug = self.debug == 'enable'
            sdk = Magento2(
                username=self.email,
                password=self.api_key,
                base_uri=self.url,
                store_code=str(self.store_code),
                debug=self.debug == 'enable'
            )
        except Exception as e:
            message+='<br/>%s'%(e)
        return dict(
            sdk=sdk,
            message=message,
        )

    @api.model
    def get_channel(self):
        result = super(MultiChannelSale, self).get_channel()
        result.append(("magento2x", "Magento v2"))
        return result

    @api.model
    def get_info_urls(self):
        urls = super(MultiChannelSale,self).get_info_urls()
        urls.update(
            magento2x = {
                'blog' : 'https://webkul.com/blog/multi-channel-magento-2-x-odoo-bridgemulti-channel-mob',
                'store': 'https://store.webkul.com/Multi-Channel-Magento-2-x-Odoo-Bridge-Multi-Channel-MOB.html',
            },
        )
        return urls

    @staticmethod
    def get_magento2x_address_hash(itemvals):
        templ_add = {
            "city":itemvals.get("city"),
            "region_code":itemvals.get("region_code"),
            "firstname":itemvals.get("firstname"),
            "lastname":itemvals.get("lastname"),
            "region":itemvals.get("region"),
            "country_id":itemvals.get("country_id"),
            "telephone":itemvals.get("telephone"),
            "street":itemvals.get("street"),
            "postcode":itemvals.get("postcode"),
            # "customer_address_id":itemvals.get("customer_address_id") or itemvals.get('customer_id')
        }
        return get_hash_dict(templ_add)

    @api.model
    def get_magento2x_store_config(self,channel_id,item):
        return literal_eval(channel_id.store_config).get(item)
