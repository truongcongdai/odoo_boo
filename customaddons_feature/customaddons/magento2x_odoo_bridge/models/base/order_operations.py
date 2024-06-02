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

    @api.model
    def magento2x_get_ship_data(self,picking_id,mapping_id,result):
        comment = 'Create For Odoo Order %s , Picking %s'%( mapping_id.order_name.name,picking_id.name)
        data ={
          "notify": True,
          "appendComment": True,
          "comment": {
            "extension_attributes": {},
            "comment": comment,
            "is_visible_on_front": 0
          }
        }
        if picking_id.carrier_tracking_ref and picking_id.carrier_id:
            data["tracks"]= [
              {
                "extension_attributes": {},
                "track_number": picking_id.carrier_tracking_ref,
                "title": picking_id.carrier_id.name,
                "carrier_code": picking_id.carrier_id.name
              }
            ]
        return data

    @api.model
    def magento2x_post_do_transfer(self, picking_id, mapping_ids, result):
        flag = True
        for i in picking_id.move_ids_without_package:
            if i.quantity_done != i.product_uom_qty:
                flag = False
        debug = self.debug=='enable'
        if flag:
            sync_vals = dict(
                status ='error',
                action_on ='order',
                action_type ='export',
            )
            res =self.get_magento2x_sdk()
            sdk = res.get('sdk')
            if debug:
                _logger.debug("do_transfer #1 %r===%r="%(res,mapping_ids))
            if sdk:
                for mapping_id in mapping_ids:
                    sync_vals['ecomstore_refrence'] ='%s(%s)'%(mapping_id.store_order_id,mapping_id.store_id)
                    sync_vals['odoo_id'] = mapping_id.odoo_order_id
                    message=''
                    data = self.magento2x_get_ship_data(picking_id,mapping_id,result)
                    res=sdk.post_orders_ship(mapping_id.store_id,data)
                    if debug:
                        _logger.debug("=do_transfer #2==%r=====%r==%r="%(data,res,sync_vals))
                    if res.get('data'):
                        sync_vals['status'] = 'success'
                        message  +='Delivery created successfully '
                    else:
                        sync_vals['status'] = 'error'
                        message  +=res.get('message')
                    sync_vals['summary'] = message
                    mapping_id.channel_id._create_sync(sync_vals)

    @api.model
    def magento2x_get_invoice_data(self,invoice_id,mapping_id,result):
        comment = 'Create For Odoo Order %s  Invoice %s'%( mapping_id.order_name.name,invoice_id.name)
        data = {
            "capture": True,
            "notify": True,
            "appendComment": True,
            "comment": {
                "extension_attributes": {},
                "comment": comment,
                "is_visible_on_front": 0
            }
        }
        return data

    @api.model
    def magento2x_post_cancel_order(self, order_id, mapping_ids, result):
        #cancel order function was not added
        message = ''
        debug = self.debug=='enable'
        res = self.get_magento2x_sdk()
        sdk =  res.get('sdk')
        sync_vals = dict(
                status ='error',
                action_on ='order',
                action_type ='export',
            )
        for mapping_id in mapping_ids:
            sync_vals['ecomstore_refrence'] ='%s(%s)'%(mapping_id.store_order_id,mapping_id.store_id)
            sync_vals['odoo_id'] = mapping_id.odoo_order_id
            res = sdk.cancel_order(mapping_id.store_id)
            if res.get('data'):
                sync_vals['status'] = 'success'
                message  +='Cancel Order successfully '
            else:
                sync_vals['status'] = 'error'
                message  +=res.get('message')
            sync_vals['summary'] = message
            if debug:
                _logger.debug("=canceled order #2==%r=====%r==="%(res,sync_vals))
            mapping_id.channel_id._create_sync(sync_vals)

    @api.model
    def magento2x_post_confirm_paid(self, invoice_id, mapping_ids, result):
        debug = self.debug=='enable'
        sync_vals = dict(
            status ='error',
            action_on ='order',
            action_type ='export',
        )
        res =self.get_magento2x_sdk()
        sdk = res.get('sdk')
        if debug:
            _logger.debug("confirm_paid #1 %r===%r="%(res,mapping_ids))
        if sdk:
            for mapping_id in mapping_ids:
                sync_vals['ecomstore_refrence'] ='%s(%s)'%(mapping_id.store_order_id,mapping_id.store_id)
                sync_vals['odoo_id'] = mapping_id.odoo_order_id
                message=''
                data =self.magento2x_get_invoice_data(invoice_id,mapping_id,result)
                res=sdk.post_orders_invoice(mapping_id.store_id,data)
                if res.get('data'):
                    sync_vals['status'] = 'success'
                    message  +='Invoice created successfully '
                else:
                    sync_vals['status'] = 'error'
                    message  +=res.get('message')
                sync_vals['summary'] = message
                if debug:
                    _logger.debug("=confirm_paid #2==%r=====%r==%r="%(data,res,sync_vals))
                mapping_id.channel_id._create_sync(sync_vals)
