import datetime
import json
from json import dumps
import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import base64
import time

_logger = logging.getLogger(__name__)


class SStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def create(self, vals):
        keys_to_check = ('quantity', 'reserved_quantity')
        res = super(SStockQuant, self).create(vals)
        if any([key in vals for key in keys_to_check]):
            warehouse_shopee = res.filtered(lambda
                                                r: r.location_id.warehouse_id and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id)
            if len(warehouse_shopee) > 0:
                for r in warehouse_shopee:
                    if not r.product_id.need_sync_shopee_stock and r.product_id.s_shopee_to_sync:
                        r.product_id.need_sync_shopee_stock = True
        return res

    def write(self, vals):
        keys_to_check = ('quantity', 'reserved_quantity', 'available_quantity')
        res = super(SStockQuant, self).write(vals)
        if any([key in vals for key in keys_to_check]):
            for rec in self:
                warehouse_shopee = rec.filtered(lambda
                                                    r: r.location_id.warehouse_id and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id)
                if len(warehouse_shopee) > 0:
                    for r in warehouse_shopee:
                        if not r.product_id.need_sync_shopee_stock and r.product_id.s_shopee_to_sync:
                            r.product_id.need_sync_shopee_stock = True
        return res

    def Shopee_push_transfer_qty(self, limit_search=False, cr_commit=False):
        try:
            s_shopee_sync_stock = self.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_shopee.s_shopee_sync_stock')
            if s_shopee_sync_stock:
                start_time = time.time()
                if not limit_search:
                    limit_search = 100
                list_product_mapping_stock_error = self.env['s.marketplace.mapping.product'].sudo().search(
                    [('s_error_type', '=', 'stock_error'), ('s_mapping_ecommerce', '=', 'shopee'),
                     ('s_product_id', '!=', 'False')]).s_product_id.ids
                s_stock_move_ids = self.env['stock.move'].sudo().search(
                    [('s_shopee_transfer_quantity', '!=', 0), ('is_push_shopee_transfer_quantity', '=', True),
                     ('product_id', 'not in', list_product_mapping_stock_error)], limit=limit_search)
                if s_stock_move_ids:
                    count = 0
                    list_product_pushed = []
                    warehouse_id = self.env['stock.warehouse'].sudo().search(
                        [('e_commerce', '=', 'shopee'), ('s_shopee_is_mapping_warehouse', '=', True)],
                        limit=1).s_shopee_location_id
                    endpoint_get_stock = "/api/v2/product/get_model_list"
                    endpoint_push_stock = "/api/v2/product/update_stock"
                    for stock_move in s_stock_move_ids:
                        if (time.time() - start_time) > 60:
                            break
                        sync_failed = False
                        product_error = []
                        if stock_move.id not in list_product_pushed:
                            vals = {
                                's_mapping_ecommerce': 'shopee',
                                "s_error_type": "product_error"
                            }
                            same_parent_product = s_stock_move_ids.filtered(lambda
                                                                                r: r.product_id.product_tmpl_id == stock_move.product_id.product_tmpl_id and r.product_id.product_tmpl_id.s_shopee_item_id == stock_move.product_id.product_tmpl_id.s_shopee_item_id and r.product_id.product_tmpl_id.s_shopee_item_id != False)
                            if same_parent_product:
                                list_model_get_api, list_child_product_pushed, stock_list = [], [], []
                                param = {
                                    'item_id': int(same_parent_product[0].product_id.product_tmpl_id.s_shopee_item_id),
                                }
                                req = self.env['s.base.integrate.shopee']._get_data_shopee(api=endpoint_get_stock,
                                                                                           param=param)
                                req_json = req.json()
                                if req.status_code == 200:
                                    response = req_json.get('response')
                                    if response:
                                        list_model_get_api = response.get('model')
                                else:
                                    vals.update({
                                        "message": str(req_json.get('message')),
                                        "error": str(req_json.get('error')),
                                    })
                                    sync_failed = True
                                for parent_product in same_parent_product:
                                    if parent_product.product_id.id not in list_child_product_pushed:
                                        child_product = same_parent_product.filtered(lambda
                                                                                         r: r.product_id == parent_product.product_id and r.product_id.s_shopee_model_id == parent_product.product_id.s_shopee_model_id and r.product_id.s_shopee_model_id != False)
                                        if child_product:
                                            total_transfer_qty = sum(child_product.mapped("s_shopee_transfer_quantity"))
                                            if len(list_model_get_api) > 0:
                                                for model_get_api in list_model_get_api:
                                                    if model_get_api.get('model_id') == int(
                                                            child_product.product_id.s_shopee_model_id):
                                                        stock_info_v2 = model_get_api.get('stock_info_v2')
                                                        if stock_info_v2:
                                                            seller_stock = stock_info_v2.get('seller_stock')
                                                            if seller_stock:
                                                                total_stock_transfer = total_transfer_qty + sum(
                                                                    stock['stock'] for stock in seller_stock)
                                                                if total_stock_transfer < 0:
                                                                    total_stock_transfer = 0
                                                                sku = {
                                                                    "model_id": int(
                                                                        child_product[0].product_id.s_shopee_model_id),
                                                                    "seller_stock": [{
                                                                        "stock": total_stock_transfer,
                                                                        "location_id": warehouse_id
                                                                    }]
                                                                }
                                                                stock_list.append(sku)
                                                                list_child_product_pushed.extend(
                                                                    child_product.product_id.ids)
                                                                break
                                                            else:
                                                                vals.update({
                                                                    "message": "check lại thông tin seller_stock của API sản phẩm",
                                                                })
                                                                sync_failed = True
                                                        else:
                                                            vals.update({
                                                                "message": "check lại thông tin stock_info_v2 của API sản phẩm",
                                                            })
                                                            sync_failed = True
                                            else:
                                                vals.update({
                                                    "message": "check lại thông tin model của API sản phẩm",
                                                })
                                                sync_failed = True
                                        else:
                                            vals.update({
                                                "message": "sản phẩm chưa được đồng bộ lên Shopee (sản phẩm con)",
                                                's_product_id': parent_product.product_id.id,
                                                's_template_id': same_parent_product.product_id.product_tmpl_id.id
                                            })
                                            sync_failed = True
                                if len(stock_list) > 0:
                                    param.update({
                                        "stock_list": stock_list
                                    })
                                    _logger.info('start check Shopee_push_transfer_qty')
                                    _logger.info(param)

                                    req = self.env['s.base.integrate.shopee']._post_data_shopee(api=endpoint_push_stock,
                                                                                                data=json.dumps(param))
                                    req_json = req.json()
                                    _logger.info(req_json)
                                    _logger.info('end check Shopee_push_transfer_qty')
                                    if req.status_code == 200:
                                        if not req_json.get('error'):
                                            same_parent_product.sudo().write({
                                                'is_push_shopee_transfer_quantity': False,
                                                's_shopee_transfer_quantity': 0,
                                            })
                                            list_product_pushed.extend(same_parent_product.ids)
                                        else:
                                            vals.update({
                                                "message": str(req_json.get('message')),
                                                "error": str(req_json.get('error')),
                                            })
                                            sync_failed = True
                                    else:
                                        sync_failed = True
                                        vals.update({
                                            "message": str(req_json.get('message')),
                                            "error": str(req_json.get('error')),
                                        })
                                    if sync_failed:
                                        for product_child in list_child_product_pushed:
                                            vals.update({
                                                's_product_id': product_child,
                                                'message': req_json.get('message'),
                                                's_template_id': same_parent_product.product_id.product_tmpl_id.id
                                            })
                                            if vals:
                                                product_error = self.env['s.marketplace.mapping.product'].sudo().create(
                                                    vals)
                            else:
                                sync_failed = True
                                vals.update({
                                    "message": "sản phẩm chưa được đồng bộ lên Shopee (sản phẩm cha)",
                                    's_product_id': stock_move.product_id.id,
                                    's_template_id': stock_move.product_id.product_tmpl_id.id
                                })
                        if not product_error and sync_failed:
                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        if cr_commit:
                            self._cr.commit()
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': 'Shopee Integrate - Synchronizing Update Stock Product When Transfer',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'Shopee_push_transfer_qty',
                'line': '0',
            })
