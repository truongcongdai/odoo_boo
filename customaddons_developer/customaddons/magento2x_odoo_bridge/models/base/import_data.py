# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, api
from logging import getLogger
_logger = getLogger(__name__)


class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    def import_magento2x(self, object, **kwargs):
        self.ensure_one()
        channel_id = self
        result = None
        debug = channel_id.debug == 'enable'
        res = channel_id.get_magento2x_sdk()
        sdk = res.get('sdk')
        if kwargs.get('message'):kwargs['message'] = ''
        if not (sdk and sdk.oauth_token):
            return None,None
        if object == 'product.category':
            result = self.env['import.categories'].import_now(channel_id, sdk, kwargs)
        elif object == 'res.partner':
            result = self.env['import.partners'].import_now(channel_id,sdk,kwargs)
        elif object == 'product.template':
            result = self.env['import.templates']._magento2x_import_products(sdk, channel_id, kwargs)
        elif object == 'sale.order':
            store_id = channel_id.get_magento2x_store_config(channel_id,'id')
            result = self.env['import.orders']._magento2x_import_orders(sdk,store_id,channel_id, kwargs)
        elif object == 'product.attribute':
            result = self.import_magento2x_attributes_sets(kwargs,sdk)
        elif object == 'delivery.carrier':
            result = []
            kwargs.update(
                message="For magento this operation gets automatically executed when order sync run, so you don't have to run it spearately."
            )
            # result.append({'store_id':"Attributes are Added"})
        else:
            pass
        if debug:
            _logger.debug('========RESULT+++++++%r+==============',[result,kwargs])
        if not result:
            result = None
        return result,kwargs

    def import_magento2x_attributes(self):
        self.ensure_one()
        vals =dict(
            channel_id=self.id
        )
        obj=self.env['import.magento2x.attributes'].create(vals)
        return obj.import_now()

    def import_magento2x_attributes_sets(self,kwargs,sdk):
        self.ensure_one()
        vals =dict(
            channel_id=self.id,
        )
        obj=self.env['import.magento2x.attributes.sets'].create(vals)
        return obj.import_now(kwargs=kwargs,sdk=sdk)
