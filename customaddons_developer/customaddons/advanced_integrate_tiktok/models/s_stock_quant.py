from odoo import fields, models, api
import time
import json


class SStockQuantInherit(models.Model):
    _inherit = ['stock.quant']

    def write(self, vals):
        keys_to_check = ('quantity', 'reserved_quantity', 'available_quantity')
        res = super(SStockQuantInherit, self).write(vals)
        if any([key in vals for key in keys_to_check]):
            for rec in self:
                warehouse_tiktok = rec.location_id.warehouse_id
                if warehouse_tiktok and warehouse_tiktok.is_mapping_warehouse and warehouse_tiktok.s_warehouse_tiktok_id and warehouse_tiktok.e_commerce == 'tiktok':
                    if warehouse_tiktok.lot_stock_id.id == rec.location_id.id:
                        if rec.product_id.to_sync_tiktok and not rec.product_id.need_sync_tiktok_stock:
                            rec.product_id.need_sync_tiktok_stock = True
        return res

    @api.model
    def create(self, vals):
        keys_to_check = ('quantity', 'reserved_quantity')
        stock_quant = super(SStockQuantInherit, self).create(vals)
        if any([key in vals for key in keys_to_check]):
            for rec in stock_quant:
                warehouse_tiktok = rec.location_id.warehouse_id
                if warehouse_tiktok and warehouse_tiktok.is_mapping_warehouse and warehouse_tiktok.s_warehouse_tiktok_id and warehouse_tiktok.e_commerce == 'tiktok':
                    if warehouse_tiktok.lot_stock_id.id == rec.location_id.id:
                        if rec.product_id.to_sync_tiktok and not rec.product_id.need_sync_tiktok_stock:
                            rec.product_id.need_sync_tiktok_stock = True
        return stock_quant

    def tiktok_push_transfer_qty(self, limit_search=False, cr_commit=False):
        try:
            s_tiktok_sync_stock = self.env['ir.config_parameter'].sudo().get_param('tiktok.s_tiktok_sync_stock')
            if s_tiktok_sync_stock:
                start_time = time.time()
                if not limit_search:
                    limit_search = None
                query_product_tiktok_error = self._cr.execute(
                    """select s_product_id from s_marketplace_mapping_product where s_product_id is not null AND s_mapping_ecommerce = 'tiktok' and (s_error_type = 'product_error' or s_error_type = 'stock_error') """)
                result_query_product_tiktok_error = [item[0] for item in self._cr.fetchall()]
                # Tìm những bản ghi stock.move có is_push_tiktok_transfer_quantity = True
                stock_moves = self.env['stock.move'].sudo().search_read(
                    domain=[('is_push_tiktok_transfer_quantity', '=', True),
                            ('s_tiktok_transfer_quantity', '!=', 0),
                            ('product_id', 'not in', result_query_product_tiktok_error)],
                    fields=['product_id', 'id', 's_tiktok_transfer_quantity'])
                if len(stock_moves) > 0:
                    stock_moves_groups = {}
                    for stock in stock_moves:
                        if stock.get('product_id')[0] in stock_moves_groups:
                            stock_moves_groups[stock.get('product_id')[0]]['s_tiktok_transfer_quantity'] += stock.get(
                                's_tiktok_transfer_quantity')
                            stock_moves_groups[stock.get('product_id')[0]]['move_ids'].append(stock.get('id'))
                        else:
                            stock_moves_groups[stock.get('product_id')[0]] = {
                                's_tiktok_transfer_quantity': stock.get('s_tiktok_transfer_quantity'),
                                'move_ids': [stock.get('id')]
                            }
                    count = 0
                    limit_while = len(stock_moves_groups)
                    sync_product_exist = []
                    while (time.time() - start_time) <= 60 and count < limit_while:
                        sync_failed = False
                        product_ids = None
                        product_error = []
                        seller_sku_list = False
                        vals = {
                            "s_mapping_ecommerce": 'tiktok',
                            "s_error_type": "stock_error",
                        }
                        stock_moves_group = list(stock_moves_groups)[count]
                        # check merge product
                        group_product_id = stock_moves_group
                        product_product = self.env['product.product'].sudo().search([('id', '=', group_product_id)])
                        if product_product:
                            if product_product.is_merge_product:
                                if product_product.marketplace_sku:
                                    seller_sku_list = product_product.marketplace_sku
                                    if product_product.default_code in product_product.marketplace_sku:
                                        product_ids = product_product
                                    else:
                                        vals.update({
                                            's_product_id': product_product.id,
                                            'message': 'SKU sản phẩm không thuộc Marketplace SKU',
                                        })
                                        sync_failed = True
                                else:
                                    vals.update({
                                        's_product_id': product_product.id,
                                        'message': 'Marketplace SKU rỗng'
                                    })
                                    sync_failed = True
                            else:
                                seller_sku_list = product_product.default_code
                                product_ids = product_product
                        else:
                            vals.update({
                                'message': 'Không tìm thấy sản phẩm, kiểm tra lại sản phẩm id = %s' % group_product_id,
                            })
                            sync_failed = True
                        if seller_sku_list:
                            vals.update({
                                "seller_sku": seller_sku_list,
                            })
                        if product_ids and product_ids.ids not in sync_product_exist:
                            # Tính số lượng điều chuyển
                            stock_transfer = stock_moves_groups[stock_moves_group].get('s_tiktok_transfer_quantity')
                            # check tiktok warehouse exist
                            warehouse_id = self.env['stock.warehouse'].sudo().search(
                                [('e_commerce', '=', 'tiktok'), ('is_mapping_warehouse', '=', True)],
                                limit=1).s_warehouse_tiktok_id
                            product = product_ids.filtered(lambda p: p.id_skus and p.product_tmpl_id.product_tiktok_id)
                            if warehouse_id and product:
                                ####Check skus_id có mapping với id sản phẩm để update stock không, nếu data trả về rỗng sẽ tạo lỗi
                                body = {
                                    'product_ids': [str(product[0].product_tiktok_id)]
                                }
                                url_get_stock = '/api/products/stock/list'
                                request = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_get_stock,
                                                                                              data=json.dumps(body))
                                request_json = request.json()
                                available_stock = 0
                                is_push = False
                                if not request_json.get('data'):
                                    vals.update({
                                        's_product_id': product_product.id,
                                        'message': 'Không tìm thấy sản phẩm khớp với sku_id = %s trên sàn Tiktok, kiểm tra và đồng bộ lại sản phẩm %s' % (
                                            str(product[0].id_skus), product[0].default_code),
                                        'data': request_json.get('data'),
                                    })
                                    sync_failed = True
                                else:
                                    if request_json.get('data').get('product_stocks'):
                                        if request_json.get('data').get('product_stocks')[0]:
                                            if request_json.get('data').get('product_stocks')[0].get('skus'):
                                                platform_stocks = request_json.get('data').get('product_stocks')[0].get(
                                                    'skus')
                                                if len(platform_stocks):
                                                    for stock in platform_stocks:
                                                        if stock.get('sku_id') == str(product[0].id_skus):
                                                            if stock.get('warehouse_stock_infos'):
                                                                for r in stock.get('warehouse_stock_infos'):
                                                                    if r.get('warehouse_id') == warehouse_id:
                                                                        available_stock = r.get('available_stock')
                                                                        is_push = True
                                                else:
                                                    sync_failed = True
                                    else:
                                        sync_failed = True
                                if not is_push:
                                    sync_failed = True
                                sku = {
                                    "id": product[0].id_skus,
                                    "stock_infos": [{
                                        "available_stock": int(stock_transfer + available_stock),
                                        "warehouse_id": warehouse_id
                                    }]
                                }
                                if product and not sync_failed:
                                    payload = {
                                        "product_id": product[0].product_tmpl_id.product_tiktok_id,
                                        "skus": [sku]
                                    }
                                    data = json.dumps(payload)
                                    url_api = '/api/products/stocks'
                                    response = self.env['base.integrate.tiktok']._put_data_tiktok(url_api=url_api,
                                                                                                  data=data)
                                    result = response.json()
                                    if response.status_code == 200:
                                        if result.get('code') == 0:
                                            if result.get('data').get('failed_skus'):
                                                vals.update({
                                                    'message': 'List of skus that failed to update',
                                                    'data': result.get('data'),
                                                })
                                                sync_failed = True
                                        else:
                                            vals.update({
                                                'message': result.get('message'),
                                                'data': result.get('data'),
                                            })
                                            sync_failed = True
                                        if not sync_failed:
                                            self._cr.execute(
                                                """UPDATE stock_move SET is_push_tiktok_transfer_quantity = FALSE AND s_tiktok_transfer_quantity = 0 WHERE id IN %s""",
                                                (tuple(stock_moves_groups[stock_moves_group].get('move_ids')),))
                                            # stock_moves.filtered(lambda r: r.product_id.id == group_product_id).sudo().write({
                                            #     'is_push_tiktok_transfer_quantity': False,
                                            #     's_tiktok_transfer_quantity': 0,
                                            # })
                                    else:
                                        vals.update({
                                            'message': result.get('message'),
                                        })
                                        sync_failed = True
                                    if sync_failed:
                                        for product in product_ids:
                                            vals.update({
                                                's_product_id': product.id,
                                            })
                                            if vals:
                                                product_error = self.env['s.marketplace.mapping.product'].sudo().create(
                                                    vals)
                            else:
                                vals.update({
                                    'message': 'Không tìm thấy kho hoặc sản phẩm trên sàn Tiktok',
                                })
                                sync_failed = True
                            sync_product_exist.append(product_ids.ids)
                        if not product_error and sync_failed:
                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        if cr_commit:
                            self._cr.commit()
                        count += 1
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Lỗi đồng bộ tồn kho sản phẩm Tiktok',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'cronjob_update_stock_skus_general_product',
                'line': '0',
            })
