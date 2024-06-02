# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api, models

class MultiChannelSkeleton(models.TransientModel):
    _inherit = 'multi.channel.skeleton'

    def set_order_shipped(self, order_id, **kwargs):
        """Cancel the order in Odoo via requests from XML-RPC
        @param order_id: Odoo Order ID
        @param context: Mandatory Dictionary with key 'ecommerce' to identify the request from E-Commerce
        @return:  A dictionary of status and status message of transaction"""
        status = True
        context = dict(self._context or {})
        status_message = ""
        backOrderModel = self.env['stock.backorder.confirmation']
        try:
            sale = self.env['sale.order'].browse(order_id)
            if sale.state == 'draft':
                res = self._ConfirmOdooOrder(sale, **kwargs)
                status_message += res['status_message']
            for picking in sale.picking_ids:
               backorder = False

               if picking.state == 'draft':
                   picking.action_confirm()
               if picking.state != 'assigned':
                   picking.action_assign()


            for picking in sale.picking_ids.filtered(
                                    lambda pickingObj: pickingObj.picking_type_code == 'outgoing' and pickingObj.state != 'done'):
                backorder = False
                # picking.force_assign()
                context = dict(self._context or {})

                context['active_id'] = picking.id
                context['picking_id'] = picking.id
                for move in picking.move_lines:
                    if move.move_line_ids:
                        for move_line in move.move_line_ids:
                                move_line.qty_done = move_line.product_uom_qty
                    else:
                        move.quantity_done = move.product_uom_qty
                if picking._check_backorder():
                    backorder=True
                    continue
                if backorder:
                    backorder_obj = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, picking.id)]})
                    backorder_obj.with_context(context).process_cancel_backorder()
                else:
                    picking.with_context(context)._action_done()
                status_message += "Order==> Shipped. "
        except Exception as e:
            status = False
            status_message = "<br/> Error in Delivering Order: %s <br/>" % str(
                    e)
        finally:
            return {
                    'status_message': status_message,
                    'status': status
            }
