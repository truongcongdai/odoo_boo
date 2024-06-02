from odoo.exceptions import ValidationError
from odoo import fields, api, models, tools
import json, random
import urllib3
import datetime, time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ..tools.api_wrapper_tiktok import validate_integrate_token

urllib3.disable_warnings()


class SProductTemplate(models.Model):
    _inherit = 'product.template'
    _order = "list_price asc"
    product_tiktok_id = fields.Char('ID sản phẩm cha Tiktok')

    # is_synced_tiktok = fields.Boolean('Đã đồng bộ sản phẩm lên tiktok', default=False)

    # @validate_integrate_token
    def cronob_sync_product_tiktok(self, limit_search=False):
        try:
            start_time = time.time()
            count = 0
            url_api = '/api/products/search'
            if not limit_search:
                limit_search = 100
            query_product_tiktok_error = self._cr.execute(
                """select s_product_id from s_marketplace_mapping_product where s_product_id is not null AND s_mapping_ecommerce = 'tiktok' and s_error_type = 'product_error' """)
            result_query_product_tiktok_error = [item[0] for item in self._cr.fetchall()]
            product_details = self.env['product.product'].sudo().search(
                [('to_sync_tiktok', '=', True), ('default_code', '!=', False), ('is_synced_tiktok', '!=', True),
                 ('id', 'not in', result_query_product_tiktok_error), ('detailed_type', '=', 'product'),
                 ('active', '=', True)], limit=limit_search)
            if len(product_details) > 0:
                limit_while = len(product_details)
                while (time.time() - start_time) <= 60 and count < limit_while:
                    sync_failed = False
                    seller_sku_list = False
                    vals = {
                        "s_mapping_ecommerce": 'tiktok',
                        "s_error_type": "product_error",
                    }
                    # check merge product
                    if not product_details[count].is_synced_tiktok:
                        if product_details[count].is_merge_product:
                            if product_details[count].marketplace_sku:
                                if product_details[count].default_code in product_details[count].marketplace_sku:
                                    seller_sku_list = product_details[count].marketplace_sku
                                else:
                                    vals.update({
                                        's_product_id': product_details[count].id,
                                        'message': 'SKU sản phẩm không thuộc Marketplace SKU',
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': product_details[count].id,
                                    'message': 'Marketplace SKU rỗng'
                                })
                                sync_failed = True
                        else:
                            seller_sku_list = product_details[count].default_code
                        if seller_sku_list:
                            vals.update({
                                "seller_sku": seller_sku_list,
                            })
                            payload = {
                                "page_number": 1,
                                "page_size": 100,
                                "seller_sku_list": [seller_sku_list]
                            }
                            request = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api,
                                                                                          data=json.dumps(payload))
                            response = request.json()
                            if request.status_code == 200:
                                if response.get('code') == 0:
                                    # check response trả về
                                    if response.get('data').get('products'):
                                        seller_product = response.get('data').get('products')
                                        for product_platfom in seller_product:
                                            if product_platfom.get('skus'):
                                                if product_platfom.get('status') == 4:
                                                    for p in product_platfom.get('skus'):
                                                        if seller_sku_list == p.get('seller_sku'):
                                                            product_details[count].sudo().write({
                                                                'id_skus': p.get('id'),
                                                                'is_synced_tiktok': True,
                                                                'need_sync_tiktok_stock': True
                                                            })
                                                            template = product_details[count].product_tmpl_id
                                                            if not template.product_tiktok_id or template.product_tiktok_id != product_platfom.get(
                                                                    'id'):
                                                                template.product_tiktok_id = product_platfom.get('id')
                                                            sync_failed = False
                                                else:
                                                    if not product_details[count].is_synced_tiktok:
                                                        vals.update({
                                                            's_product_id': product_details[count].id,
                                                            'message': 'Sản phẩm không ở trạng thái live'
                                                        })
                                                        sync_failed = True
                                            else:
                                                vals.update({
                                                    's_product_id': product_details[count].id,
                                                    'message': 'Không có seller_sku trong respone trả về'
                                                })
                                                sync_failed = True
                                    else:
                                        vals.update({
                                            's_product_id': product_details[count].id,
                                            'message': 'Không tìm thấy sản phẩm trên sàn Tiktok có SKU = %s ' % seller_sku_list
                                        })
                                        sync_failed = True
                                else:
                                    vals.update({
                                        's_product_id': product_details[count].id,
                                        'message': response.get('message')
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': product_details[count].id,
                                    'message': response.get('message')
                                })
                                sync_failed = True
                        if sync_failed:
                            self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        count += 1
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Lỗi đồng bộ sản phẩm Tiktok',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
            })

    # @validate_integrate_token
    def cronjob_update_stock_skus_general_product(self, limit_search=False, cr_commit=False):
        try:
            s_tiktok_sync_stock = self.env['ir.config_parameter'].sudo().get_param('tiktok.s_tiktok_sync_stock')
            if s_tiktok_sync_stock:
                start_time = time.time()
                url_api = '/api/products/stocks'
                count = 0
                if not limit_search:
                    limit_search = 100
                query_product_product = self._cr.execute(
                    """SELECT id, is_merge_product, marketplace_sku, default_code FROM product_product WHERE default_code IS NOT NULL AND is_synced_tiktok IS TRUE 
                    AND (need_sync_tiktok_stock IS NULL OR need_sync_tiktok_stock IS TRUE)
                    AND id NOT IN (SELECT s_product_id FROM s_marketplace_mapping_product WHERE s_product_id IS NOT NULL and s_mapping_ecommerce = 'tiktok' and s_error_type = 'stock_error') AND active=TRUE
                    LIMIT %s""", (limit_search,))
                product_details = [item for item in self._cr.dictfetchall()]
                if len(product_details) > 0:
                    limit_while = len(product_details)
                    # san pham da dong bo
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
                        # check merge product
                        if product_details[count].get('is_merge_product'):
                            if product_details[count].get('marketplace_sku'):
                                seller_sku_list = product_details[count].get('marketplace_sku')
                                if product_details[count].get('default_code') in product_details[count].get(
                                        'marketplace_sku'):
                                    product_ids = self.env['product.product'].search(
                                        [("marketplace_sku", "=", product_details[count].get('marketplace_sku'))])
                                else:
                                    vals.update({
                                        's_product_id': product_details[count].get('id'),
                                        'message': 'SKU sản phẩm không thuộc Marketplace SKU',
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': product_details[count].get('id'),
                                    'message': 'Marketplace SKU rỗng'
                                })
                                sync_failed = True
                        else:
                            seller_sku_list = product_details[count].get('default_code')
                            product_ids = self.env['product.product'].search(
                                [("default_code", "=", seller_sku_list)])
                        if seller_sku_list:
                            vals.update({
                                "seller_sku": seller_sku_list,
                            })
                        if product_ids and product_ids.ids not in sync_product_exist:
                            # tong ton kho Tiktok - lay theo so luong co the ban
                            available_stock = int(sum(product_ids.stock_quant_ids.filtered(
                                lambda r: r.location_id.warehouse_id.is_mapping_warehouse == True
                                          and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).mapped(
                                "available_quantity")))
                            # check tiktok warehouse exist
                            warehouse_id = self.env['stock.warehouse'].sudo().search(
                                [('e_commerce', '=', 'tiktok'), ('is_mapping_warehouse', '=', True)],
                                limit=1).s_warehouse_tiktok_id
                            product = product_ids.filtered(lambda p: p.id_skus and p.product_tmpl_id.product_tiktok_id)
                            if warehouse_id and product:
                                ####Check skus_id có mapping với id sản phẩm để update stock không, nếu data trả về rỗng sẽ tạo lỗi
                                body = {
                                    'sku_ids': [str(product[0].id_skus)]
                                }
                                url_get_stock = '/api/products/stock/list'
                                request = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_get_stock,
                                                                                              data=json.dumps(body))
                                request_json = request.json()
                                if not request_json.get('data'):
                                    vals.update({
                                        's_product_id': product_details[count].get('id'),
                                        'message': 'Không tìm thấy sản phẩm khớp với sku_id = %s trên sàn Tiktok, kiểm tra và đồng bộ lại sản phẩm %s' % (
                                            str(product[0].id_skus), product[0].default_code),
                                        'data': request_json.get('data'),
                                    })
                                    sync_failed = True
                                sku = {
                                    "id": product[0].id_skus,
                                    "stock_infos": [{
                                        "available_stock": available_stock,
                                        "warehouse_id": warehouse_id
                                    }]
                                }
                                if product and not sync_failed:
                                    payload = {
                                        "product_id": product[0].product_tmpl_id.product_tiktok_id,
                                        "skus": [sku]
                                    }
                                    data = json.dumps(payload)
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
                                                product_ids.sudo().write({
                                                    'need_sync_tiktok_stock': False
                                                })
                                        else:
                                            vals.update({
                                                'message': result.get('message'),
                                                'data': result.get('data'),
                                            })
                                            sync_failed = True
                                    else:
                                        vals.update({
                                            'message': result.get('message'),
                                        })
                                        sync_failed = True
                                    if sync_failed:
                                        for product in product_ids:
                                            vals.update({
                                                's_product_id': product.id,
                                                # 'message': result.get('message'),
                                            })
                                            if vals:
                                                product_error = self.env['s.marketplace.mapping.product'].sudo().create(
                                                    vals)

                                    check_time = time.time() - start_time
                                    print(
                                        'check time sync stock %s' % check_time + 'check time number stock %s' % count)
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

    def cronjob_sync_stock_according_time_setting_tiktok(self, limit_search=False, cr_commit=False):
        # Synchronize according to time setting
        try:
            s_tiktok_sync_stock = self.env['ir.config_parameter'].sudo().get_param('tiktok.s_tiktok_sync_stock')
            sync_stock_automate = False
            if s_tiktok_sync_stock:
                sync_stock_automate = s_tiktok_sync_stock
            run_cron = False
            sync_stock_end_of_day = self.env['ir.config_parameter'].sudo().get_param(
                'tiktok.s_tiktok_sync_stock_end_of_day')
            time_start = self.env['ir.config_parameter'].sudo().get_param('tiktok.s_tiktok_set_time_start')
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
                url_api = '/api/products/stocks'
                count = 0
                if not limit_search:
                    limit_search = 100
                query_product_product = self._cr.execute(
                    """SELECT id, is_merge_product, marketplace_sku, default_code FROM product_product WHERE default_code IS NOT NULL AND is_synced_tiktok IS TRUE 
                    AND need_sync_tiktok_stock IS TRUE
                    AND id NOT IN (SELECT s_product_id FROM s_marketplace_mapping_product WHERE s_product_id IS NOT NULL and s_mapping_ecommerce = 'tiktok' and s_error_type = 'stock_error') AND active=TRUE
                    LIMIT %s""", (limit_search,))
                # AND (need_sync_tiktok_stock IS NULL OR need_sync_tiktok_stock IS TRUE)
                product_details = [item for item in self._cr.dictfetchall()]
                if len(product_details) > 0:
                    if sync_stock_automate:
                        self.env['ir.config_parameter'].sudo().set_param("tiktok.s_tiktok_sync_stock", False)
                    limit_while = len(product_details)
                    # san pham da dong bo
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
                        # check merge product
                        if product_details[count].get('is_merge_product'):
                            if product_details[count].get('marketplace_sku'):
                                seller_sku_list = product_details[count].get('marketplace_sku')
                                if product_details[count].get('default_code') in product_details[count].get(
                                        'marketplace_sku'):
                                    product_ids = self.env['product.product'].search(
                                        [("marketplace_sku", "=", product_details[count].get('marketplace_sku'))])
                                else:
                                    vals.update({
                                        's_product_id': product_details[count].get('id'),
                                        'message': 'SKU sản phẩm không thuộc Marketplace SKU',
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': product_details[count].get('id'),
                                    'message': 'Marketplace SKU rỗng'
                                })
                                sync_failed = True
                        else:
                            seller_sku_list = product_details[count].get('default_code')
                            product_ids = self.env['product.product'].search(
                                [("default_code", "=", seller_sku_list)])
                        if seller_sku_list:
                            vals.update({
                                "seller_sku": seller_sku_list,
                            })
                        if product_ids and product_ids.ids not in sync_product_exist:
                            # tong ton kho Tiktok - lay theo so luong co the ban
                            available_stock = int(sum(product_ids.stock_quant_ids.filtered(
                                lambda r: r.location_id.warehouse_id.is_mapping_warehouse == True
                                          and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).mapped(
                                "available_quantity")))
                            # check tiktok warehouse exist
                            warehouse_id = self.env['stock.warehouse'].sudo().search(
                                [('e_commerce', '=', 'tiktok'), ('is_mapping_warehouse', '=', True)],
                                limit=1).s_warehouse_tiktok_id
                            product = product_ids.filtered(
                                lambda p: p.id_skus and p.product_tmpl_id.product_tiktok_id)
                            if warehouse_id and product:
                                ####Check skus_id có mapping với id sản phẩm để update stock không, nếu data trả về rỗng sẽ tạo lỗi
                                body = {
                                    'sku_ids': [str(product[0].id_skus)]
                                }
                                url_get_stock = '/api/products/stock/list'
                                request = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_get_stock,
                                                                                              data=json.dumps(body))
                                request_json = request.json()
                                if not request_json.get('data'):
                                    vals.update({
                                        's_product_id': product_details[count].get('id'),
                                        'message': 'Không tìm thấy sản phẩm khớp với sku_id = %s trên sàn Tiktok, kiểm tra và đồng bộ lại sản phẩm %s' % (
                                            str(product[0].id_skus), product[0].default_code),
                                        'data': request_json.get('data'),
                                    })
                                    sync_failed = True
                                sku = {
                                    "id": product[0].id_skus,
                                    "stock_infos": [{
                                        "available_stock": available_stock,
                                        "warehouse_id": warehouse_id
                                    }]
                                }
                                if product and not sync_failed:
                                    payload = {
                                        "product_id": product[0].product_tmpl_id.product_tiktok_id,
                                        "skus": [sku]
                                    }
                                    data = json.dumps(payload)
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
                                                self._cr.execute(
                                                    """UPDATE stock_move SET is_push_tiktok_transfer_quantity = FALSE AND s_tiktok_transfer_quantity = 0
                                                     WHERE is_push_tiktok_transfer_quantity = TRUE AND s_tiktok_transfer_quantity != 0 and id in %s""",
                                                    (tuple(product_ids.ids),))
                                                self._cr.execute(
                                                    """UPDATE product_product SET need_sync_tiktok_stock = FALSE WHERE id in %s""",
                                                    (tuple(product_ids.ids),))
                                        else:
                                            vals.update({
                                                'message': result.get('message'),
                                                'data': result.get('data'),
                                            })
                                            sync_failed = True
                                    else:
                                        vals.update({
                                            'message': result.get('message'),
                                        })
                                        sync_failed = True
                                    if sync_failed:
                                        for product in product_ids:
                                            vals.update({
                                                's_product_id': product.id,
                                                # 'message': result.get('message'),
                                            })
                                            if vals:
                                                product_error = self.env[
                                                    's.marketplace.mapping.product'].sudo().create(
                                                    vals)

                                    check_time = time.time() - start_time
                                    print(
                                        'check time sync stock %s' % check_time + 'check time number stock %s' % count)
                            sync_product_exist.append(product_ids.ids)
                        if not product_error and sync_failed:
                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        self._cr.commit()
                        count += 1
                else:
                    next_scheduler = str(tz_time_start + relativedelta(days=int(1)))
                    self.env['ir.config_parameter'].sudo().set_param('tiktok.s_tiktok_set_time_start', next_scheduler)
                if sync_stock_automate:
                    self.env['ir.config_parameter'].sudo().set_param("tiktok.s_tiktok_sync_stock", True)
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
