from odoo import fields, models, api
from odoo.exceptions import ValidationError, _logger
import json
import time


class SProductProduct(models.Model):
    _inherit = ['product.product']

    s_shopee_model_id = fields.Char('Model Id Shopee')
    s_shopee_is_synced = fields.Boolean('Đã đồng bộ sản phẩm lên shopee', default=False)
    s_shopee_to_sync = fields.Boolean('Đồng bộ Shopee', default=False, track_visibility='always')
    need_sync_shopee_stock = fields.Boolean(default=True)

    def _compute_need_sync_shopee_stock(self):
        for rec in self:
            if not rec.need_sync_shopee_stock:
                rec.need_sync_shopee_stock = True

    @api.onchange('s_shopee_to_sync')
    def _onchange_delete_mapping_product_shopee(self):
        updated_product_product_ids = []
        ids_template = []
        for rec in self:
            if not rec.s_shopee_to_sync:
                updated_product_product_ids.append(rec._origin.id)
                ids_template.append(rec._origin.product_tmpl_id.id)
        if len(updated_product_product_ids) > 0:
            product_domain_list = [str(e) for e in updated_product_product_ids]
            product_domain_str = '(' + ','.join(product_domain_list) + ')'
            if '(False)' not in product_domain_str:
                self._cr.execute(
                    'update product_product set  s_shopee_is_synced = FALSE, s_shopee_model_id = null where id in ' + product_domain_str)
        if len(ids_template) > 0:
            id_tmp = set(ids_template)
            str_tmp = str(id_tmp.pop())
            if 'False' not in str_tmp:
                self._cr.execute(
                    'update product_template set s_shopee_check_sync = FALSE where id = ' + str_tmp)

    # def write(self, vals):
    #     res = super(SProductProduct, self).write(vals)
    #     if 'active' in vals:
    #         for rec in self:
    #             warehouse_shopee = rec.stock_quant_ids.filtered(lambda r: r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id and r.location_id.warehouse_id and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True)
    #             if len(warehouse_shopee) > 0:
    #                 for r in warehouse_shopee:
    #                     if not r.product_id.need_sync_shopee_stock and r.product_id.s_shopee_is_synced:
    #                         r.product_id.need_sync_shopee_stock = True
    #     return res

    def btn_sync_stock_realtime_shopee(self, cr_commit=False):
        try:
            for rec in self:
                start_time = time.time()
                url_api = '/api/v2/product/update_stock'
                sync_product_exist = []
                if rec.s_shopee_model_id:
                    while (time.time() - start_time) <= 60:
                        stock_list = []
                        product_error = []
                        sync_failed = False
                        product_ids = None
                        seller_sku_list = False
                        vals = {
                            's_mapping_ecommerce': 'shopee',
                            "s_error_type": "stock_error"
                        }
                        if rec.is_merge_product:
                            if rec.marketplace_sku:
                                seller_sku_list = rec.marketplace_sku
                                if rec.default_code in rec.marketplace_sku:
                                    product_ids = self.env['product.product'].search(
                                        [(
                                            "marketplace_sku", "=",
                                            seller_sku_list.encode('ascii', 'ignore').decode("utf-8")),
                                            ("default_code", "in", seller_sku_list.split(','))])
                                else:
                                    vals.update({
                                        's_product_id': rec.id,
                                        'message': 'SKU sản phẩm không thuộc Marketplace SKU',
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': rec.id,
                                    'message': 'Marketplace SKU rỗng'
                                })
                                sync_failed = True
                        else:
                            seller_sku_list = rec.default_code
                            product_ids = rec
                        if seller_sku_list:
                            vals.update({
                                "seller_sku": seller_sku_list,
                            })
                        if product_ids and not set(product_ids.ids).issubset(sync_product_exist):
                            total_quantity = int(sum(product_ids.stock_quant_ids.filtered(lambda
                                                                                              r: r.location_id.warehouse_id and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).mapped(
                                "available_quantity")))
                            # check shopee warehouse exist
                            warehouse_id = self.env['stock.warehouse'].sudo().search(
                                [('e_commerce', '=', 'shopee'), ('s_shopee_is_mapping_warehouse', '=', True)],
                                limit=1).s_shopee_location_id
                            product = product_ids.filtered(
                                lambda p: p.s_shopee_model_id and p.product_tmpl_id.s_shopee_item_id)
                            if warehouse_id != False and product:
                                sku = {
                                    "model_id": int(product[0].s_shopee_model_id),
                                    "seller_stock": [{
                                        "stock": total_quantity,
                                        "location_id": warehouse_id
                                    }]
                                }
                                stock_list.append(sku)
                                payload = {
                                    "item_id": int(product[0].product_tmpl_id.s_shopee_item_id),
                                    "stock_list": stock_list
                                }
                                req = self.env['s.base.integrate.shopee']._post_data_shopee(api=url_api,
                                                                                            data=json.dumps(payload))
                                req_json = req.json()
                                _logger.info('start check cronjob_update_stock_skus_general_product_shopee')
                                _logger.info(req)
                                _logger.info(req_json)
                                _logger.info(payload)
                                _logger.info('end check cronjob_update_stock_skus_general_product_shopee')
                                if req.status_code == 200:
                                    if not req_json.get('error'):
                                        product_ids.sudo().write({
                                            'need_sync_shopee_stock': False
                                        })
                                    else:
                                        vals.update({
                                            "message": str(req_json.get('message')),
                                            "error": str(req_json.get('error')),
                                        })
                                        sync_failed = True
                                else:
                                    sync_failed = True
                                    self.env['ir.config_parameter'].sudo().set_param(
                                        'advanced_integrate_shopee.is_error_token_shopee', 'True')
                                    vals.update({
                                        "message": str(req_json.get('message')),
                                        "error": str(req_json.get('error')),
                                    })
                                if sync_failed:
                                    for product in product_ids:
                                        vals.update({
                                            's_product_id': product.id,
                                            'message': req_json.get('message'),
                                            's_template_id': product[0].product_tmpl_id.id
                                        })
                                        if vals:
                                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(
                                                vals)
                            sync_product_exist += product_ids.ids
                        if not product_error and sync_failed:
                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        if cr_commit:
                            self._cr.commit()
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': 'Shopee Integrate - Synchronizing Update Stock Product',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'cronjob_update_stock_skus_general_product_shopee',
                'line': '0',
            })
