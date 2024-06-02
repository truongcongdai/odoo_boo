from odoo import fields, models, api
from odoo.exceptions import ValidationError
import datetime, time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class SStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def create(self, vals):
        res = super(SStockQuant, self).create(vals)
        keys_to_check = ('quantity', 'reserved_quantity', 'available_quantity')
        if any([key in vals for key in keys_to_check]):
            for rec in self:
                if rec.location_id.warehouse_id.is_push_lazada:
                    if not rec.product_id.need_sync_lazada_stock and rec.product_id.to_sync_lazada:
                        rec.product_id.need_sync_lazada_stock = True
        return res

    def write(self, vals):
        keys_to_check = ('quantity', 'reserved_quantity', 'available_quantity')
        res = super(SStockQuant, self).write(vals)
        if any([key in vals for key in keys_to_check]):
            for rec in self:
                if rec.location_id.warehouse_id.is_push_lazada:
                    if not rec.product_id.need_sync_lazada_stock and rec.product_id.to_sync_lazada:
                        rec.product_id.need_sync_lazada_stock = True
        return res

    def search_product_need_sync(self):
        defective_product = self.env['s.marketplace.mapping.product'].sudo().search(
            [('s_mapping_ecommerce', '=', 'lazada'), ('s_error_type', '=', 'stock_error')])
        product_variant_ids = self.env['product.product'].search([('to_sync_lazada', '=', True),
                                                                  ('need_sync_lazada_stock', '=', True),
                                                                  ('s_lazada_is_mapped_product', '=', True),
                                                                  ('id', 'not in',
                                                                   defective_product.mapped('s_product_id.id'))],
                                                                 limit=15)
        return product_variant_ids

    # def cronjob_sync_stock_lazada(self, product_variant_ids=None, error_stock=None):
    #     s_lazada_sync_stock = self.env['ir.config_parameter'].sudo().get_param('intergrate_lazada.s_lazada_sync_stock')
    #     if s_lazada_sync_stock:
    #         start_time = time.time()
    #         timeout = 60
    #         limiting = 100
    #         api = '/product/stock/sellable/update'
    #         sku = []
    #         product_ids = []
    #         # search san pham can sync stock
    #         if product_variant_ids == None and error_stock == None:
    #             product_variant_ids = self.search_product_need_sync()
    #         # build param sync stock
    #         if product_variant_ids:
    #             for product_variant_id in product_variant_ids:
    #                 if product_variant_id.need_sync_lazada_stock:
    #                     stock_quant_ids = int(sum(product_variant_id.stock_quant_ids.filtered(
    #                         lambda r: r.location_id.warehouse_id.is_push_lazada == True).mapped(
    #                         "available_quantity")))
    #                     value = {
    #                         "ItemId": product_variant_id.s_lazada_item_id,
    #                         "SkuId": product_variant_id.s_lazada_sku_id,
    #                         "SellerSku": product_variant_id.s_lazada_seller_sku,
    #                         "SellableQuantity": stock_quant_ids
    #                     }
    #                     if product_variant_id.is_merge_product:
    #                         product_merge_ids = product_variant_id.search(
    #                             [('marketplace_sku', '=', product_variant_id.marketplace_sku),
    #                              ('is_merge_product', '=', True), ('to_sync_lazada', '=', True)])
    #                         quantity_available = product_merge_ids.stock_quant_ids.filtered(
    #                             lambda r: r.location_id.warehouse_id.is_push_lazada == True).mapped(
    #                             "available_quantity")
    #                         value.update({"SellableQuantity": sum(quantity_available)})
    #                         value.update({"SellerSku": product_variant_id.marketplace_sku})
    #                     sku.append(value)
    #                     product_ids.append(product_variant_id)
    #                     if (time.time() - start_time) >= timeout and len(sku) > limiting:
    #                         break
    #         if sku:
    #             parameters = {"payload":
    #                 {
    #                     "Request": {
    #                         "Product": {
    #                             "Skus": {
    #                                 "Sku": sku
    #                             }
    #                         }
    #                     }
    #                 }
    #             }
    #             res = self.env['base.integrate.lazada']._post_data_lazada(api, parameters)
    #             try:
    #                 # code = 0 hoac code = 501 deu update ton va hien thi loi
    #                 if res.get('code') == '0' or res.get('code') == '501':
    #                     if res.get('detail'):
    #                         for r in res.get('detail'):
    #                             vals = {'code': int(res.get('code')),
    #                                     'message': r.get('message'),
    #                                     'error': r.get('field'),
    #                                     'request_id': res.get('request_id'),
    #                                     'data': str(r),
    #                                     's_mapping_ecommerce': 'lazada',
    #                                     's_error_type': 'stock_error'}
    #                             if r.get('seller_sku'):
    #                                 for product in product_ids:
    #                                     if product.s_lazada_seller_sku == str(r.get('seller_sku')):
    #                                         if r.get('field') in ['ItemId', 'SkuId', 'SellerSku']:
    #                                             product.write({
    #                                                 's_lazada_is_mapped_product': False
    #                                             })
    #                                         else:
    #                                             vals.update({
    #                                                 's_product_id': product.id,
    #                                                 'seller_sku': product.default_code,
    #                                             })
    #                                             product_error = self.env['s.marketplace.mapping.product'].sudo().create(
    #                                                 vals)
    #                                         product_ids.remove(product)
    #                             elif r.get('item_id'):
    #                                 for product in product_ids:
    #                                     if product.s_lazada_item_id == str(r.get('item_id')):
    #                                         if r.get('field') in ['ItemId', 'SkuId', 'SellerSku']:
    #                                             product.write({
    #                                                 's_lazada_is_mapped_product': False
    #                                             })
    #                                         else:
    #                                             vals.update({
    #                                                 's_product_id': product.id,
    #                                                 'seller_sku': product.default_code,
    #                                             })
    #                                             product_error = self.env['s.marketplace.mapping.product'].sudo().create(
    #                                                 vals)
    #                                         product_ids.remove(product)
    #                             elif r.get('sku_id'):
    #                                 for product in product_ids:
    #                                     if product.s_lazada_sku_id == str(r.get('sku_id')) or product.s_lazada_item_id == str(r.get('sku_id')):
    #                                         """
    #                                         case: product.s_lazada_item_id == str(r.get('sku_id'))
    #                                         param = {'ItemId': '2163649657', 'SkuId': '10215597871', 'SellerSku': '8930000914538',
    #                                          'SellableQuantity': 2}
    #                                         res = {'code': 'E0501', 'field': 'bizCheck', 'message': 'NO_EDITING_OTHERS_ITEM', 'sku_id': 2163649657}
    #                                         Response Lazada tra ve sku_id nhung thuc chat lai la ItemId
    #                                         """
    #                                         if r.get('field') in ['ItemId', 'SkuId', 'SellerSku']:
    #                                             product.write({
    #                                                 's_lazada_is_mapped_product': False
    #                                             })
    #                                         else:
    #                                             vals.update({
    #                                                 's_product_id': product.id,
    #                                                 'seller_sku': product.default_code,
    #                                             })
    #                                             product_error = self.env['s.marketplace.mapping.product'].sudo().create(
    #                                                 vals)
    #                                         product_ids.remove(product)
    #                             else:
    #                                 self.env['ir.logging'].sudo().create({
    #                                     'name': 'cronjob_sync_stock_lazada',
    #                                     'type': 'server',
    #                                     'dbname': 'boo',
    #                                     'level': 'ERROR',
    #                                     'path': 'url',
    #                                     'message': str(res) if res else None,
    #                                     'func': 'api_cronjob_sync_stock_lazada',
    #                                     'line': '0',
    #                                 })
    #                                 product_ids.remove(product_ids)
    #                     if len(product_ids) > 0:
    #                         for product in product_ids:
    #                             product.write({
    #                                 'need_sync_lazada_stock': False
    #                             })
    #                     self.env['ir.logging'].sudo().create({
    #                         'name': 'cronjob_sync_stock_lazada',
    #                         'type': 'server',
    #                         'dbname': 'boo',
    #                         'level': 'INFO',
    #                         'path': 'url',
    #                         'message': str(res) if res else None,
    #                         'func': 'api_cronjob_sync_stock_lazada',
    #                         'line': '0',
    #                     })
    #                 else:
    #                     for product in product_ids:
    #                         self.env['s.marketplace.mapping.product'].sudo().create({
    #                             's_product_id': product.id,
    #                             'seller_sku': product.default_code,
    #                             'message': res.get('message'),
    #                             'error': res.get('message'),
    #                             'request_id': res.get('request_id'),
    #                             'data': parameters,
    #                             's_mapping_ecommerce': 'lazada',
    #                             's_error_type': 'stock_error'
    #                         })
    #             except Exception as e:
    #                 self.env['ir.logging'].sudo().create({
    #                     'name': 'cronjob_sync_stock_lazada',
    #                     'type': 'server',
    #                     'dbname': 'boo',
    #                     'level': 'ERROR',
    #                     'path': api,
    #                     'message': str(e) + str(parameters),
    #                     'func': 'api_cronjob_sync_stock_lazada',
    #                     'line': '0',
    #                 })

    def cronjob_sync_stock_according_time_setting_lazada(self, product_variant_ids=None, error_stock=None):
        run_cron = False
        sync_stock_end_of_day = self.env['ir.config_parameter'].sudo().get_param(
            'lazada.s_lazada_sync_stock_end_of_day')
        time_start = self.env['ir.config_parameter'].sudo().get_param('lazada.s_lazada_set_time_start')
        tz_time_start = False
        if sync_stock_end_of_day == 'True':
            time_now = datetime.now()
            if time_start:
                tz_time_start = datetime.strptime(time_start, '%Y-%m-%d %H:%M:%S')
                if tz_time_start:
                    if tz_time_start <= time_now:
                        run_cron = True
        if run_cron:
            start_time = time.time()
            timeout = 60
            limiting = 100
            api = '/product/stock/sellable/update'
            sku = []
            product_ids = []
            sync_manual = False
            # search san pham can sync stock
            if product_variant_ids == None and error_stock == None:
                product_variant_ids = self.search_product_need_sync()
            else:
                sync_manual = True
            # build param sync stock
            if product_variant_ids:
                ### Clear stock_move set is_push_lazada_transfer_quantity = False, s_lazada_transfer_quantity = 0 trước khi push toàn bộ tồn kho
                ###TH1: user đồng bộ lại bằng tay
                if sync_manual:
                    query_stock_move = self._cr.execute("""
                        SELECT id FROM stock_move WHERE is_push_lazada_transfer_quantity = TRUE AND s_lazada_transfer_quantity != 0 
                        AND product_id NOT IN (SELECT s_product_id FROM s_marketplace_mapping_product WHERE s_product_id IS NOT NULL AND s_mapping_ecommerce = 'lazada' AND (s_error_type = 'product_error' OR s_error_type = 'stock_error'))
                        AND product_id IN %s
                    """, (tuple(product_variant_ids.mapped('id')),))
                    result_query_stock_move = [item[0] for item in self._cr.fetchall()]
                ###TH2: Đồng bộ tự động
                else:
                    query_stock_move = self._cr.execute("""
                        SELECT id FROM stock_move WHERE is_push_lazada_transfer_quantity = TRUE AND s_lazada_transfer_quantity != 0 AND product_id NOT IN 
                        (SELECT s_product_id FROM s_marketplace_mapping_product WHERE s_product_id IS NOT NULL AND s_mapping_ecommerce = 'lazada' AND (s_error_type = 'product_error' OR s_error_type = 'stock_error'))
                    """)
                    result_query_stock_move = [item[0] for item in self._cr.fetchall()]
                if len(result_query_stock_move):
                    self._cr.execute("""
                        UPDATE stock_move SET is_push_lazada_transfer_quantity = FALSE, s_lazada_transfer_quantity = 0 WHERE id IN %s
                    """, (tuple(result_query_stock_move),))
                ###Điều kiện để dừng cronjob push tồn điều chuyển
                s_lazada_sync_stock = self.env['ir.config_parameter'].sudo().get_param('intergrate_lazada.s_lazada_sync_stock')
                if s_lazada_sync_stock == 'True':
                    self.env['ir.config_parameter'].sudo().set_param('intergrate_lazada.s_lazada_sync_stock', 'False')
                for product_variant_id in product_variant_ids:
                    if product_variant_id.need_sync_lazada_stock:
                        stock_quant_ids = int(sum(product_variant_id.stock_quant_ids.filtered(
                            lambda r: r.location_id.warehouse_id.is_push_lazada == True).mapped(
                            "available_quantity")))
                        value = {
                            "ItemId": product_variant_id.s_lazada_item_id,
                            "SkuId": product_variant_id.s_lazada_sku_id,
                            "SellerSku": product_variant_id.s_lazada_seller_sku,
                            "SellableQuantity": stock_quant_ids
                        }
                        if product_variant_id.is_merge_product:
                            product_merge_ids = product_variant_id.search(
                                [('marketplace_sku', '=', product_variant_id.marketplace_sku),
                                 ('is_merge_product', '=', True), ('to_sync_lazada', '=', True)])
                            quantity_available = product_merge_ids.stock_quant_ids.filtered(
                                lambda r: r.location_id.warehouse_id.is_push_lazada == True).mapped(
                                "available_quantity")
                            value.update({"SellableQuantity": sum(quantity_available)})
                            value.update({"SellerSku": product_variant_id.marketplace_sku})
                        sku.append(value)
                        product_ids.append(product_variant_id)
                        if (time.time() - start_time) >= timeout and len(sku) > limiting:
                            break
            else:
                next_scheduler = str(tz_time_start + relativedelta(days=int(1)))
                self.env['ir.config_parameter'].sudo().set_param('lazada.s_lazada_set_time_start', next_scheduler)
                self.env['ir.config_parameter'].sudo().set_param('intergrate_lazada.s_lazada_sync_stock', 'True')
            if sku:
                parameters = {"payload":
                    {
                        "Request": {
                            "Product": {
                                "Skus": {
                                    "Sku": sku
                                }
                            }
                        }
                    }
                }
                res = self.env['base.integrate.lazada']._post_data_lazada(api, parameters)
                try:
                    # code = 0 hoac code = 501 deu update ton va hien thi loi
                    if res.get('code') == '0' or res.get('code') == '501':
                        if res.get('detail'):
                            for r in res.get('detail'):
                                vals = {'code': int(res.get('code')),
                                        'message': r.get('message'),
                                        'error': r.get('field'),
                                        'request_id': res.get('request_id'),
                                        'data': str(r),
                                        's_mapping_ecommerce': 'lazada',
                                        's_error_type': 'stock_error'}
                                if r.get('seller_sku'):
                                    for product in product_ids:
                                        if product.s_lazada_seller_sku == str(r.get('seller_sku')):
                                            if r.get('field') in ['ItemId', 'SkuId', 'SellerSku']:
                                                product.write({
                                                    's_lazada_is_mapped_product': False
                                                })
                                            else:
                                                vals.update({
                                                    's_product_id': product.id,
                                                    'seller_sku': product.default_code,
                                                })
                                                product_error = self.env['s.marketplace.mapping.product'].sudo().create(
                                                    vals)
                                            product_ids.remove(product)
                                elif r.get('item_id'):
                                    for product in product_ids:
                                        if product.s_lazada_item_id == str(r.get('item_id')):
                                            if r.get('field') in ['ItemId', 'SkuId', 'SellerSku']:
                                                product.write({
                                                    's_lazada_is_mapped_product': False
                                                })
                                            else:
                                                vals.update({
                                                    's_product_id': product.id,
                                                    'seller_sku': product.default_code,
                                                })
                                                product_error = self.env['s.marketplace.mapping.product'].sudo().create(
                                                    vals)
                                            product_ids.remove(product)
                                elif r.get('sku_id'):
                                    for product in product_ids:
                                        if product.s_lazada_sku_id == str(r.get('sku_id')) or product.s_lazada_item_id == str(r.get('sku_id')):
                                            """
                                            case: product.s_lazada_item_id == str(r.get('sku_id'))
                                            param = {'ItemId': '2163649657', 'SkuId': '10215597871', 'SellerSku': '8930000914538',
                                             'SellableQuantity': 2}
                                            res = {'code': 'E0501', 'field': 'bizCheck', 'message': 'NO_EDITING_OTHERS_ITEM', 'sku_id': 2163649657}
                                            Response Lazada tra ve sku_id nhung thuc chat lai la ItemId
                                            """
                                            if r.get('field') in ['ItemId', 'SkuId', 'SellerSku']:
                                                product.write({
                                                    's_lazada_is_mapped_product': False
                                                })
                                            else:
                                                vals.update({
                                                    's_product_id': product.id,
                                                    'seller_sku': product.default_code,
                                                })
                                                product_error = self.env['s.marketplace.mapping.product'].sudo().create(
                                                    vals)
                                            product_ids.remove(product)
                                else:
                                    self.env['ir.logging'].sudo().create({
                                        'name': 'cronjob_sync_stock_lazada',
                                        'type': 'server',
                                        'dbname': 'boo',
                                        'level': 'ERROR',
                                        'path': 'url',
                                        'message': str(res) if res else None,
                                        'func': 'api_cronjob_sync_stock_lazada',
                                        'line': '0',
                                    })
                                    product_ids.remove(product_ids)
                        if len(product_ids) > 0:
                            for product in product_ids:
                                product.write({
                                    'need_sync_lazada_stock': False
                                })
                        self.env['ir.logging'].sudo().create({
                            'name': 'cronjob_sync_stock_lazada',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'INFO',
                            'path': 'url',
                            'message': str(res) if res else None,
                            'func': 'api_cronjob_sync_stock_lazada',
                            'line': '0',
                        })
                    else:
                        for product in product_ids:
                            self.env['s.marketplace.mapping.product'].sudo().create({
                                's_product_id': product.id,
                                'seller_sku': product.default_code,
                                'message': res.get('message'),
                                'error': res.get('message'),
                                'request_id': res.get('request_id'),
                                'data': parameters,
                                's_mapping_ecommerce': 'lazada',
                                's_error_type': 'stock_error'
                            })
                except Exception as e:
                    self.env['ir.logging'].sudo().create({
                        'name': 'cronjob_sync_stock_lazada',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': api,
                        'message': str(e) + str(parameters),
                        'func': 'api_cronjob_sync_stock_lazada',
                        'line': '0',
                    })

    def lazada_push_transfer_qty(self, limit_search=False, cr_commit=False):
        try:
            s_lazada_sync_stock = self.env['ir.config_parameter'].sudo().get_param('intergrate_lazada.s_lazada_sync_stock')
            if s_lazada_sync_stock == 'True':
                start_time = time.time()
                api = '/product/stock/sellable/update'
                if not limit_search:
                    limit_search = 100
                query_lazada_product_error = self._cr.execute(
                    """select s_product_id from s_marketplace_mapping_product where s_product_id is not null and s_mapping_ecommerce = 'lazada' and (s_error_type = 'product_error' or s_error_type = 'stock_error') """)
                result_query_lazada_product_error = [item[0] for item in self._cr.fetchall()]
                #Tìm những bản ghi stock.move có is_push_lazada_transfer_quantity = True
                stock_moves = self.env['stock.move'].sudo().search(
                    [('is_push_lazada_transfer_quantity', '=', True), ('s_lazada_transfer_quantity', '!=', 0), ('product_id', 'not in', result_query_lazada_product_error)],
                    limit=limit_search)
                if len(stock_moves) > 0:
                    stock_moves_group = self.env['stock.move'].sudo().read_group(
                        domain=[('id', 'in', stock_moves.mapped('id'))], fields=['s_lazada_transfer_quantity'],
                        groupby=['product_id'])
                    count = 0
                    limit_while = len(stock_moves_group)
                    while (time.time() - start_time) <= 60 and count < limit_while:
                        sku = []
                        sync_failed = False
                        vals = {
                            "s_mapping_ecommerce": 'lazada',
                            "s_error_type": "stock_error",
                        }
                        group_product_id = stock_moves_group[count]['product_id'][0]
                        product_product = self.env['product.product'].sudo().search([('id', '=', group_product_id)])
                        if product_product:
                            stock_move = stock_moves.filtered(lambda r: r.product_id.id == group_product_id)
                            product_variant_id = product_product
                            value = {
                                "ItemId": product_variant_id.s_lazada_item_id,
                                "SkuId": product_variant_id.s_lazada_sku_id,
                                "SellerSku": product_variant_id.s_lazada_seller_sku,
                                "SellableQuantity": 0
                            }
                            seller_sku = product_variant_id.default_code
                            if product_variant_id.is_merge_product:
                                value.update({"SellerSku": product_variant_id.marketplace_sku})
                                seller_sku = product_variant_id.marketplace_sku
                            product_data = self.env['base.integrate.lazada']._get_data_lazada('/products/get', {'sku_seller_list':'["'+seller_sku+'"]'})
                            if product_data.get('code') == "0":
                                if product_data.get('data'):
                                    if product_data.get('data').get('products'):
                                        for rec in product_data.get('data').get('products')[0].get('skus'):
                                            if rec.get('SellerSku') == value.get('SellerSku') and rec.get('SkuId') == int(value.get('SkuId')):
                                                value.update({"SellableQuantity": int(rec.get('Available') + stock_moves_group[count].get('s_lazada_transfer_quantity'))})
                                                sku.append(value)
                                else:
                                    vals.update({
                                        's_product_id': product_variant_id.id,
                                        'message': 'Không tìm thấy sản phẩm khớp với SkuId = %s trên sàn Lazada, kiểm tra và đồng bộ lại sản phẩm %s' % (
                                            str(product_variant_id.s_lazada_sku_id), product_variant_id.default_code),
                                        'data': product_data.get('data'),
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': product_variant_id.id,
                                    'message': 'Không tìm thấy sản phẩm khớp với SkuId = %s trên sàn Lazada, kiểm tra và đồng bộ lại sản phẩm %s' % (
                                        str(product_variant_id.s_lazada_sku_id), product_variant_id.default_code),
                                    'data': product_data.get('data'),
                                })
                                sync_failed = True
                            if sku:
                                parameters = {"payload":
                                    {
                                        "Request": {
                                            "Product": {
                                                "Skus": {
                                                    "Sku": sku
                                                }
                                            }
                                        }
                                    }
                                }
                                res = self.env['base.integrate.lazada']._post_data_lazada(api, parameters)
                                # code = 0 hoac code = 501 deu update ton va hien thi loi
                                if res.get('code') == '0' or res.get('code') == '501':
                                    if res.get('detail'):
                                        for r in res.get('detail'):
                                            vals.update({
                                                'code': int(res.get('code')),
                                                'message': r.get('message'),
                                                'error': r.get('field'),
                                                'request_id': res.get('request_id'),
                                                'data': str(r),
                                                's_product_id': product_variant_id.id,
                                                'seller_sku': product_variant_id.default_code,
                                            })
                                            sync_failed = True
                                    else:
                                        stock_move.sudo().write({
                                            'is_push_lazada_transfer_quantity': False,
                                            's_lazada_transfer_quantity': 0,
                                        })
                                else:
                                    vals.update({
                                        'message': res.get('message'),
                                        'data': str(res),
                                        's_product_id': product_variant_id.id,
                                    })
                                    sync_failed = True
                        else:
                            vals.update({
                                'message': 'Không tìm thấy sản phẩm, kiểm tra lại sản phẩm id = %s' % group_product_id,
                            })
                            sync_failed = True
                        if sync_failed:
                            self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        if cr_commit:
                            self._cr.commit()
                        count += 1
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Lỗi đồng bộ tồn kho Lazada theo điều chuyển',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'lazada_push_transfer_qty',
                'line': '0',
            })
