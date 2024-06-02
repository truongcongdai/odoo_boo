import hashlib
import hmac
import json
from datetime import date
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import requests

from odoo import fields, models
from odoo.exceptions import ValidationError, _logger
from ..tools.api_wrapper_shopee import validate_integrate_token


class SProductTemplate(models.Model):
    _inherit = ['product.template']

    s_shopee_item_id = fields.Char(string='ID sản phẩm cha Shopee')
    s_shopee_is_push = fields.Boolean(default=False)
    s_shopee_check_sync = fields.Boolean(default=False)

    def _cron_sync_product_shopee(self, limmit_search=False, cr_commit=False):
        try:
            start_time = time.time()
            if not limmit_search:
                limmit_search = 100
            query_product_synced_shopee = self._cr.execute(
                """select id from product_template where s_shopee_is_push is TRUE and active=TRUE and (s_shopee_check_sync is FALSE or s_shopee_check_sync is null) and detailed_type = 'product' 
                and id NOT IN (SELECT s_template_id FROM s_marketplace_mapping_product where s_template_id is not NULL and s_mapping_ecommerce = 'shopee' and s_error_type = 'product_error') LIMIT %s;""",
                (limmit_search,))
            result_query_product_synced_shopee = [item[0] for item in self._cr.fetchall()]
            template_sync = self.env['product.template'].sudo().browse(result_query_product_synced_shopee)
            templates = template_sync.product_variant_ids.filtered(
                lambda r: r.s_shopee_is_synced == False).product_tmpl_id
            count = 0
            if len(templates) > 0:
                while (time.time() - start_time) <= 60 and count < len(templates):
                    item_sku = False
                    sync_failed = False
                    vals = {
                        's_mapping_ecommerce': 'shopee',
                        "s_error_type": "product_error"
                    }
                    if templates[count].ma_san_pham:
                        item_sku = templates[count].ma_san_pham
                    if item_sku:
                        api = '/api/v2/product/search_item'
                        param = {
                            'item_sku': item_sku,
                            'page_size': 10,
                        }
                        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=api, param=param)
                        req_json = req.json()
                        if req.status_code == 200:
                            response = req_json.get('response')
                            if response:
                                item_id_list = response.get('item_id_list')
                                if item_id_list:
                                    for item in item_id_list:
                                        api_model = "/api/v2/product/get_model_list"
                                        param_model = {
                                            "item_id": item
                                        }
                                        req_model = self.env['s.base.integrate.shopee']._get_data_shopee(api=api_model,
                                                                                                         param=param_model)
                                        req_model_json = req_model.json()
                                        if req_model.status_code == 200:
                                            response_model = req_model_json.get('response')
                                            if response_model:
                                                list_model = response_model.get('model')
                                                if list_model:
                                                    count1 = 0
                                                    for model in list_model:
                                                        model_sku = model.get('model_sku')
                                                        if model_sku is not None:
                                                            products = self.env['product.product']
                                                            if "," not in model_sku:
                                                                products = self.env['product.product'].sudo().search(
                                                                    [('default_code', '=', model_sku),
                                                                     ('s_shopee_to_sync', '=', True)])
                                                            else:
                                                                products = self.env['product.product'].sudo().search([(
                                                                    'marketplace_sku',
                                                                    '=',
                                                                    (
                                                                        model_sku.encode(
                                                                            'ascii',
                                                                            'ignore')).decode(
                                                                        "utf-8")),
                                                                    (
                                                                        'default_code',
                                                                        'in',
                                                                        model_sku.split(
                                                                            ',')),
                                                                    (
                                                                        's_shopee_to_sync',
                                                                        '=',
                                                                        True)])
                                                            if products:
                                                                products.sudo().write({
                                                                    's_shopee_is_synced': True,
                                                                    's_shopee_model_id': model.get('model_id')
                                                                })
                                                                if any([res != str(item) for res in
                                                                        products.product_tmpl_id.mapped(
                                                                            's_shopee_item_id')]):
                                                                    products.product_tmpl_id.sudo().write({
                                                                        's_shopee_check_sync': True,
                                                                        's_shopee_item_id': item
                                                                    })
                                                                count1 += 1
                                                        else:
                                                            vals.update({
                                                                's_template_id': templates[count].id,
                                                                'message': 'Kiểm tra lại sản phẩm trên Shopee! model_sku None response_model: ' + str(
                                                                    response_model),
                                                            })
                                                            sync_failed = True
                                                    if count1 == 0:
                                                        vals.update({
                                                            's_template_id': templates[count].id,
                                                            'message': 'Kiểm tra lại sản phẩm trên Shopee! count = 0 response_model: ' + str(
                                                                response_model),
                                                            "item_sku": item_sku,
                                                        })
                                                        sync_failed = True
                                                else:
                                                    vals.update({
                                                        's_template_id': templates[count].id,
                                                        'message': 'Kiểm tra lại sản phẩm trên Shopee! model rỗng response_model: ' + str(
                                                            response_model),
                                                        "item_sku": str(item_sku),
                                                    })
                                                    sync_failed = True
                                            else:
                                                vals.update({
                                                    's_template_id': templates[count].id,
                                                    'message': 'Kiểm tra lại sản phẩm trên Shopee! response rỗng response_model: ' + str(
                                                        response_model),
                                                    "item_sku": str(item_sku),
                                                })
                                                sync_failed = True
                                        else:
                                            vals.update({
                                                's_template_id': templates[count].id,
                                                'message': req_model_json.get('message'),
                                                "item_sku": str(item_sku),
                                            })
                                            sync_failed = True
                                else:
                                    vals.update({
                                        's_template_id': templates[count].id,
                                        'message': 'Kiểm tra lại sản phẩm trên Shopee! response_item: ' + str(response),
                                        "item_sku": item_sku,
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_template_id': templates[count].id,
                                    'message': 'Kiểm tra lại sản phẩm trên Shopee! response_item: ' + str(response),
                                    "item_sku": item_sku,
                                })
                                sync_failed = True
                        else:
                            self.env['ir.config_parameter'].sudo().set_param(
                                'advanced_integrate_shopee.is_error_token_shopee', 'True')
                            vals.update({
                                "s_template_id": templates[count].id,
                                "message": str(req_json.get('message')),
                                "error": str(req_json.get('error')),
                                "item_sku": str(item_sku),
                            })
                            sync_failed = True
                    else:
                        vals.update({
                            "s_template_id": templates[count].id,
                            "item_sku": str(item_sku),
                            "message": "Không có mã sản phẩm",
                        })
                        sync_failed = True
                    if sync_failed:
                        if vals:
                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                    if cr_commit:
                        self._cr.commit()
                    count += 1
            elif all(x == True for x in template_sync.product_variant_ids.mapped('s_shopee_is_synced')) and len(
                    result_query_product_synced_shopee) > 0:
                template_sync.sudo().write({
                    's_shopee_check_sync': True
                })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Shopee Integrate - Synchronizing Product',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': '_cron_sync_product_shopee',
                'line': '0',
            })

    # sync stock from odoo to shopee
    def cronjob_update_stock_skus_general_product_shopee(self, limit_search=False, cr_commit=False):
        try:
            s_shopee_sync_stock = self.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_shopee.s_shopee_sync_stock')
            if s_shopee_sync_stock:
                start_time = time.time()
                count = 0
                url_api = '/api/v2/product/update_stock'
                if not limit_search:
                    limit_search = 100
                query_product_product = self._cr.execute(
                    """SELECT DISTINCT marketplace_sku, id, is_merge_product, default_code, need_sync_shopee_stock FROM product_product WHERE s_shopee_is_synced IS TRUE and (need_sync_shopee_stock IS NULL OR need_sync_shopee_stock IS TRUE) and active=TRUE and id NOT IN (SELECT s_product_id FROM s_marketplace_mapping_product where s_product_id is not NULL and s_mapping_ecommerce = 'shopee' and s_error_type = 'stock_error') LIMIT %s""",
                    (limit_search,))
                product_details = [item for item in self._cr.dictfetchall()]
                sync_product_exist = []
                if len(product_details) > 0:
                    while (time.time() - start_time) <= 60 and count < len(product_details):
                        stock_list = []
                        product_error = []
                        sync_failed = False
                        product_ids = None
                        seller_sku_list = False
                        vals = {
                            's_mapping_ecommerce': 'shopee',
                            "s_error_type": "stock_error"
                        }
                        if product_details[count].get('is_merge_product'):
                            if product_details[count].get('marketplace_sku'):
                                seller_sku_list = product_details[count].get('marketplace_sku')
                                if product_details[count].get('default_code') in product_details[count].get(
                                        'marketplace_sku'):
                                    product_ids = self.env['product.product'].search(
                                        [(
                                            "marketplace_sku", "=",
                                            seller_sku_list.encode('ascii', 'ignore').decode("utf-8")),
                                            ("default_code", "in", seller_sku_list.split(','))])
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
                            product_ids = self.env['product.product'].search([("default_code", "=", seller_sku_list)])
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

                                check_time = time.time() - start_time
                                print('check time sync stock %s' % check_time + 'check time number stock %s' % count)
                            sync_product_exist += product_ids.ids
                        if not product_error and sync_failed:
                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        if cr_commit:
                            self._cr.commit()
                        count += 1
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

    def cronjob_sync_stock_according_time_setting_shopee(self, limit_search=False, cr_commit=False):
        # Synchronize according to time setting
        try:
            run_cron = False
            sync_stock_end_of_day = self.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_shopee.s_shopee_sync_stock_end_of_day')
            time_start = self.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_shopee.s_shopee_set_time_start')
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
                count = 0
                url_api = '/api/v2/product/update_stock'
                if not limit_search:
                    limit_search = 100
                query_product_product = self._cr.execute(
                    """SELECT DISTINCT marketplace_sku, id, is_merge_product, default_code, need_sync_shopee_stock FROM product_product WHERE s_shopee_is_synced IS TRUE and (need_sync_shopee_stock IS NULL OR need_sync_shopee_stock IS TRUE) and active=TRUE and id NOT IN (SELECT s_product_id FROM s_marketplace_mapping_product where s_product_id is not NULL and s_mapping_ecommerce = 'shopee' and s_error_type = 'stock_error') LIMIT %s""",
                    (limit_search,))
                product_details = [item for item in self._cr.dictfetchall()]
                sync_product_exist = []
                if len(product_details) > 0:
                    self._cr.execute("""UPDATE stock_move SET is_push_shopee_transfer_quantity = FALSE, s_shopee_transfer_quantity = 0 WHERE id in 
                                        (SELECT id FROM stock_move WHERE is_push_shopee_transfer_quantity = TRUE AND s_shopee_transfer_quantity != 0 AND product_id NOT IN 
                                        (SELECT s_product_id FROM s_marketplace_mapping_product WHERE s_product_id IS NOT NULL AND s_mapping_ecommerce = 'shopee' AND (s_error_type = 'product_error' OR s_error_type = 'stock_error')))""")
                    ###Điều kiện để dừng cronjob push tồn điều chuyển
                    self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.s_shopee_sync_stock', False)
                    while (time.time() - start_time) <= 60 and count < len(product_details):
                        stock_list = []
                        product_error = []
                        sync_failed = False
                        product_ids = None
                        seller_sku_list = False
                        vals = {
                            's_mapping_ecommerce': 'shopee',
                            "s_error_type": "stock_error"
                        }
                        if product_details[count].get('is_merge_product'):
                            if product_details[count].get('marketplace_sku'):
                                seller_sku_list = product_details[count].get('marketplace_sku')
                                if product_details[count].get('default_code') in product_details[count].get(
                                        'marketplace_sku'):
                                    product_ids = self.env['product.product'].search(
                                        [(
                                            "marketplace_sku", "=",
                                            seller_sku_list.encode('ascii', 'ignore').decode("utf-8")),
                                            ("default_code", "in", seller_sku_list.split(','))])
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
                            product_ids = self.env['product.product'].search([("default_code", "=", seller_sku_list)])
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
                                    break
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

                                check_time = time.time() - start_time
                                print('check time sync stock %s' % check_time + 'check time number stock %s' % count)
                            sync_product_exist += product_ids.ids
                        if not product_error and sync_failed:
                            product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        if cr_commit:
                            self._cr.commit()
                        count += 1
                else:
                    next_scheduler = str(tz_time_start + relativedelta(days=int(1)))
                    self.env['ir.config_parameter'].sudo().set_param('tiktok.s_tiktok_set_time_start', next_scheduler)
                    self.env['ir.config_parameter'].sudo().set_param('advanced_integrate_shopee.s_shopee_sync_stock', True)

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

