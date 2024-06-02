from odoo import fields, models
from odoo.exceptions import ValidationError
import time, json


class SMarketplaceMappingProduct(models.Model):
    _name = 's.marketplace.mapping.product'
    _description = 'Mapping Product Marketplace'
    _order = "create_date desc"

    s_product_id = fields.Many2one('product.product', string="Product product")
    s_template_id = fields.Many2one('product.template', string="Product template")
    item_sku = fields.Char(string="SKU Template")
    seller_sku = fields.Char(string="SKU Product")
    code = fields.Integer(string="Code")
    message = fields.Char(string="Message")
    error = fields.Char(string="Error")
    request_id = fields.Char(string="Request id")
    data = fields.Char(string="Data")
    s_check_mapping_product = fields.Boolean(string='Đã đồng bộ', default=False)
    s_tiktok_mapping_product = fields.Boolean(string="Đồng bộ Tiktok", default=False)
    s_shopee_mapping_product = fields.Boolean(string="Đồng bộ Shopee", default=False)
    s_lazada_mapping_product = fields.Boolean(string="Đồng bộ Lazada", default=False)
    s_mkp_deactive_product = fields.Boolean(string="Deactive", default=False)
    s_mapping_ecommerce = fields.Selection([
        ('tiktok', 'Đồng bộ Tiktok'),
        ('shopee', 'Đồng bộ Shopee'),
        ('lazada', 'Đồng bộ Lazada')
    ], string='Đổng bộ tồn kho', default=False)
    s_error_type = fields.Selection([
        ('product_error', 'Lỗi đồng bộ sản phẩm'),
        ('stock_error', 'Lỗi đồng bộ tồn kho'),
    ], string='Loại lỗi', default=False)

    def compute_s_mapping_ecommerce(self):
        for rec in self:
            if rec.s_tiktok_mapping_product:
                rec.s_mapping_ecommerce = "tiktok"
            elif rec.s_shopee_mapping_product:
                rec.s_mapping_ecommerce = "shopee"
            elif rec.s_lazada_mapping_product:
                rec.s_mapping_ecommerce = "lazada"

    def func_mapping_product_error(self, template_synced, templates):
        count = 0
        try:
            if len(templates) > 0:
                while count < len(templates):
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
                                                            products = templates[count].product_variant_ids.filtered(
                                                                lambda r: (
                                                                        r.default_code == model_sku and r.s_shopee_to_sync == True and r.s_shopee_is_synced == False and r.s_shopee_model_id == False) if "," not in model_sku else (
                                                                        r.marketplace_sku == (
                                                                    model_sku.encode('ascii', 'ignore')).decode(
                                                                    "utf-8") and r.default_code in model_sku.split(',')
                                                                        and r.s_shopee_to_sync == True and r.s_shopee_is_synced == False and r.s_shopee_model_id == False))
                                                            if products:
                                                                products.sudo().write({
                                                                    's_shopee_is_synced': True,
                                                                    's_shopee_model_id': model.get('model_id')
                                                                })
                                                                if templates[count].s_shopee_item_id != item:
                                                                    templates[count].sudo().write({
                                                                        's_shopee_check_sync': True,
                                                                        's_shopee_item_id': item
                                                                    })
                                                                count1 += 1
                                                        else:
                                                            vals.update({
                                                                's_template_id': templates[count].id,
                                                                'message': 'Kiểm tra lại sản phẩm trên Shopee! response_model: ' + str(
                                                                    response_model),
                                                            })
                                                            sync_failed = True
                                                    if count1 == 0:
                                                        vals.update({
                                                            's_template_id': templates[count].id,
                                                            'message': 'Kiểm tra lại sản phẩm trên Shopee! response_model: ' + str(
                                                                response_model),
                                                            "item_sku": item_sku,
                                                        })
                                                        sync_failed = True
                                                else:
                                                    vals.update({
                                                        's_template_id': templates[count].id,
                                                        'message': 'Kiểm tra lại sản phẩm trên Shopee! response_model: ' + str(
                                                            response_model),
                                                        "item_sku": str(item_sku),
                                                    })
                                                    sync_failed = True
                                            else:
                                                vals.update({
                                                    's_template_id': templates[count].id,
                                                    'message': 'Kiểm tra lại sản phẩm trên Shopee! response_model: ' + str(
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
                    count += 1
            elif all(x == True for x in template_synced.product_variant_ids.mapped('s_shopee_is_synced')):
                template_synced.sudo().write({
                    's_shopee_check_sync': True
                })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Shopee Integrate - Synchronizing Product Error',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'func_mapping_product_error',
                'line': '0',
            })

    def func_mapping_stock_shopee_error(self, product_details):
        try:
            count = 0
            url_api = '/api/v2/product/update_stock'
            sync_product_exist = []
            while count < len(product_details):
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
                                    'message': str(req_json.get('message')),
                                    's_template_id': product[0].product_tmpl_id.id
                                })
                                if vals:
                                    product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)

                    sync_product_exist += product_ids.ids
                if not product_error and sync_failed:
                    product_error = self.env['s.marketplace.mapping.product'].sudo().create(vals)
                count += 1
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Shopee Integrate - Synchronizing Update Stock Error',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'mass_action_mapping_stock_product',
                'line': '0',
            })

    def mass_action_mapping_product(self):
        if len(self) > 0:
            product_shopee = self.filtered(
                lambda r: r.s_mapping_ecommerce == 'shopee' and r.s_error_type == 'product_error')
            product_tiktok = self.filtered(
                lambda r: r.s_mapping_ecommerce == 'tiktok' and r.s_error_type == 'product_error')
            if len(product_shopee) > 0:
                templates = product_shopee.s_template_id.product_variant_ids.filtered(
                    lambda r: r.s_shopee_is_synced == False).product_tmpl_id
                if len(templates) > 0:
                    self.env['s.marketplace.mapping.product'].sudo().func_mapping_product_error(
                        template_synced=product_shopee.s_template_id, templates=templates)
                    product_shopee.unlink()
            if len(product_tiktok) > 0:
                post_data = product_tiktok.filtered(lambda r: r.s_product_id.to_sync_tiktok == True
                                                              and r.s_product_id.default_code and r.s_product_id.detailed_type == 'product' and not r.s_product_id.is_synced_tiktok)
                if len(post_data) > 0:
                    self.resync_product_tiktok(data_product=post_data)
                    post_data.unlink()

    def mass_action_mapping_stock_product(self):
        # Sync stock Lazada for product error
        if len(self) > 0:
            stock_shopee = self.filtered(
                lambda r: r.s_mapping_ecommerce == 'shopee' and r.s_error_type == 'stock_error')
            stock_tiktok = self.filtered(
                lambda r: r.s_mapping_ecommerce == 'tiktok' and r.s_error_type == 'stock_error')
            stock_lazada = self.filtered(
                lambda r: r.s_mapping_ecommerce == 'lazada' and r.s_error_type == 'stock_error')
            if len(stock_lazada) > 0:
                product_variant_ids = []
                for rec in stock_lazada:
                    if rec.s_mapping_ecommerce == 'lazada' and rec.s_error_type == 'stock_error':
                        product_variant_ids.append(rec.s_product_id)
                        rec.s_product_id.sudo().write({
                            'need_sync_lazada_stock': True
                        })
                        rec.unlink()
                if len(product_variant_ids) > 0:
                    self.env['stock.quant'].sudo().cronjob_sync_stock_according_time_setting_lazada(product_variant_ids=product_variant_ids,
                                                                             error_stock='stock_error')
            if len(stock_tiktok) > 0:
                post_data = stock_tiktok.filtered(lambda r: r.s_product_id.is_synced_tiktok == True)
                if len(post_data) > 0:
                    self.resync_update_stock_product_tiktok(data=post_data)
                    post_data.unlink()
            if len(stock_shopee) > 0:
                query_product_product = self._cr.execute(
                    """SELECT DISTINCT marketplace_sku, id, is_merge_product, default_code, need_sync_shopee_stock FROM product_product WHERE s_shopee_is_synced IS TRUE and id in %s""",
                    (tuple(stock_shopee.s_product_id.mapped("id")),))
                product_details = [item for item in self._cr.dictfetchall()]
                if len(product_details) > 0:
                    self.env['s.marketplace.mapping.product'].sudo().func_mapping_stock_shopee_error(
                        product_details=product_details)
                    stock_shopee.unlink()

    def resync_update_stock_product_tiktok(self, data):
        try:
            url_api = '/api/products/stocks'
            count = 0
            product_details = data.mapped('s_product_id')
            ###Trước khi đồng bộ lại tồn kho cần đồng bộ lại sản phẩm để tránh trường hợp ID sản phẩm sàn tiktok bị thay đổi
            self.resync_product_tiktok(data)
            if len(product_details) > 0:
                sync_product_exist = []
                for detail in product_details:
                    sync_failed = False
                    product_ids = None
                    product_error = []
                    seller_sku_list = False
                    vals = {
                        "s_mapping_ecommerce": 'tiktok',
                        "s_error_type": "stock_error",
                    }
                    if detail.is_merge_product:
                        if detail.marketplace_sku:
                            seller_sku_list = detail.marketplace_sku
                            if detail.default_code in detail.marketplace_sku:
                                product_ids = self.env['product.product'].search(
                                    [("marketplace_sku", "=", detail.marketplace_sku)])
                            else:
                                vals.update({
                                    's_product_id': product_details[count].get('id'),
                                    'message': 'SKU sản phẩm không thuộc Marketplace SKU',
                                })
                                sync_failed = True
                        else:
                            vals.update({
                                's_product_id': product_details[count].get('id'),
                                'message': 'Marketplace SKU rỗng',
                            })
                            sync_failed = True
                    else:
                        seller_sku_list = detail.default_code
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
                            request = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_get_stock, data=json.dumps(body))
                            request_json = request.json()
                            if not request_json.get('data'):
                                vals.update({
                                    's_product_id': product_details[count].get('id'),
                                    'message': 'Không tìm thấy sản phẩm khớp với sku_id = %s trên sàn Tiktok, kiểm tra và đồng bộ lại sản phẩm %s' % (
                                    str(product[0].id_skus), product.default_code),
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
                                        self._cr.execute(
                                            """UPDATE stock_move SET is_push_tiktok_transfer_quantity = FALSE AND s_tiktok_transfer_quantity = 0
                                             WHERE is_push_tiktok_transfer_quantity = TRUE AND s_tiktok_transfer_quantity != 0 and id in %s""",
                                            (tuple(product_ids.ids),))
                                        self._cr.execute(
                                            """UPDATE product_product SET need_sync_tiktok_stock = FALSE WHERE id in %s""",
                                            (tuple(product_ids.ids),))
                                        # product_ids.sudo().write({
                                        #     'need_sync_tiktok_stock': False
                                        # })
                                    else:
                                        vals.update({
                                            'message': result.get('message'),
                                            'data': result.get('data'),
                                        })
                                        sync_failed = True
                                else:
                                    sync_failed = True
                                if sync_failed:
                                    for product in product_ids:
                                        vals.update({
                                            's_product_id': product.id,
                                            'message': result.get('message'),
                                        })
                                        if vals:
                                            product_error = self.sudo().create(vals)
                        sync_product_exist.append(product_ids.ids)
                    if not product_error and sync_failed:
                        product_error = self.sudo().create(vals)
                    count += 1
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Lỗi đồng bộ lại tồn kho sản phẩm Tiktok',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'cronjob_update_stock_skus_general_product',
                'line': '0',
            })

    def resync_product_tiktok(self, data_product):
        try:
            url_api = '/api/products/search'
            product_details = data_product.mapped('s_product_id')
            product_details.sudo().write({
                'is_synced_tiktok': False
            })
            if len(product_details) > 0:
                for detail in product_details:
                    sync_failed = False
                    seller_sku_list = False
                    vals = {
                        "s_mapping_ecommerce": 'tiktok',
                        "s_error_type": "product_error",
                    }
                    # check merge product
                    if not detail.is_synced_tiktok:
                        if detail.is_merge_product:
                            if detail.marketplace_sku:
                                if detail.default_code in detail.marketplace_sku:
                                    seller_sku_list = detail.marketplace_sku
                                else:
                                    vals.update({
                                        's_product_id': detail.id,
                                        'message': 'SKU sản phẩm không thuộc Marketplace SKU',
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': detail.id,
                                    'message': 'Marketplace SKU rỗng'
                                })
                                sync_failed = True
                        else:
                            seller_sku_list = detail.default_code
                        if seller_sku_list:
                            vals.update({
                                "seller_sku": seller_sku_list,
                            })
                            payload = {
                                "page_number": 1,
                                "page_size": 100,
                                "seller_sku_list": [seller_sku_list]
                            }
                            request = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload))
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
                                                            detail.sudo().write({
                                                                'id_skus': p.get('id'),
                                                                'is_synced_tiktok': True,
                                                                'need_sync_tiktok_stock': True
                                                            })
                                                            template = detail.product_tmpl_id
                                                            if not template.product_tiktok_id or template.product_tiktok_id != product_platfom.get('id'):
                                                                template.product_tiktok_id = product_platfom.get('id')
                                            else:
                                                vals.update({
                                                    's_product_id': detail.id,
                                                    'message': 'Không có seller_sku trong respone trả về'
                                                })
                                                sync_failed = True
                                    else:
                                        vals.update({
                                            's_product_id': detail.id,
                                            'message': 'Không tìm thấy sản phẩm trên sàn Tiktok có SKU = %s ' % seller_sku_list
                                        })
                                        sync_failed = True
                                else:
                                    vals.update({
                                        's_product_id': detail.id,
                                        'message': response.get('message')
                                    })
                                    sync_failed = True
                            else:
                                vals.update({
                                    's_product_id': detail.id,
                                    'message': response.get('message')
                                })
                                sync_failed = True
                        if sync_failed:
                            self.sudo().create(vals)
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Lỗi đồng bộ lại sản phẩm Tiktok',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
            })
