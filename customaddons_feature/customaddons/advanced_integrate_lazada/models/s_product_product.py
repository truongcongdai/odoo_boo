from odoo import fields, models, api
import time, json


class SProductProduct(models.Model):
    _inherit = 'product.product'

    need_sync_lazada_stock = fields.Boolean(string='Đồng bộ tồn kho Lazada', default=True)
    is_shipping_fee_lazada = fields.Boolean(string='Phí vận chuyển Lazada')
    is_promo_seller_lazada = fields.Boolean(string='Khuyến mãi nhà bán Lazada')
    is_promo_lazada = fields.Boolean(string='Khuyến mãi Lazada')
    to_sync_lazada = fields.Boolean('Đồng bộ Lazada', default=False, track_visibility='always')
    s_lazada_is_mapped_product = fields.Boolean(
        string='Lazada sản phẩm đã được mapping', default=False)
    s_lazada_seller_sku = fields.Char(
        string='Lazada Seller Sku')
    s_lazada_sku_id = fields.Char(
        string='Lazada Sku ID')
    s_lazada_item_id = fields.Char(
        string='Lazada Item ID')
    """
        s_lazada_is_mapped_product: Da mapping san pham
        s_lazada_seller_sku: SellerSku tren Lazada
        s_lazada_sku_id: SkuId tren Lazada
    """

    @api.onchange('to_sync_lazada')
    def _constrains_delete_mapping_product_lazada(self):
        updated_product_product_ids = []
        for rec in self:
            if not rec.to_sync_lazada:
                updated_product_product_ids.append(rec._origin.id)
        if len(updated_product_product_ids) > 0:
            product_domain_list = [str(e) for e in updated_product_product_ids]
            product_domain_str = '(' + ','.join(product_domain_list) + ')'
            if '(False)' not in product_domain_str:
                self._cr.execute(
                    'update product_product set s_lazada_is_mapped_product = FALSE, s_lazada_seller_sku = null, s_lazada_sku_id = null where id in ' + product_domain_str)

    def cron_lazada_sync_product(self, limit_search=False):
        try:
            start_time = time.time()
            count = 0
            url_api = '/product/item/get'
            if not limit_search:
                limit_search = 100
            query_lazada_product_error = self._cr.execute(
                """select s_product_id from s_marketplace_mapping_product where s_product_id is not null and s_mapping_ecommerce = 'lazada' and s_error_type = 'product_error' """)
            result_query_lazada_product_error = [item[0] for item in self._cr.fetchall()]
            product_details = self.env['product.product'].sudo().search(
                [('to_sync_lazada', '=', True), ('default_code', '!=', False),
                 ('s_lazada_is_mapped_product', '!=', True),
                 ('id', 'not in', result_query_lazada_product_error), ('detailed_type', '=', 'product')],
                limit=limit_search)
            if len(product_details) > 0:
                limit_while = len(product_details)
                while (time.time() - start_time) <= 60 and count < limit_while:
                    sync_failed = False
                    seller_sku_list = False
                    vals = {
                        "s_mapping_ecommerce": 'lazada',
                        "s_error_type": "product_error",
                    }
                    # check merge product
                    if not product_details[count].s_lazada_is_mapped_product:
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
                                'seller_sku': seller_sku_list
                            }
                            product_item_id = False
                            # Get product detail
                            product_data = self.env['base.integrate.lazada']._get_data_lazada('/products/get', {'sku_seller_list':'["'+seller_sku_list+'"]'})
                            if product_data.get('data'):
                                data = product_data.get('data')
                                if len(data.get('products'))>0:
                                    product = data.get('products')[0]
                                    if product:
                                        product_item_id = product.get('item_id')
                                        if product_item_id:
                                            payload = {
                                                'item_id': product_item_id
                                            }
                                        else:
                                            vals.update({
                                                's_product_id': product_details[count].id,
                                                'message': 'Không có item_id trong respone trả về'
                                            })
                                            sync_failed = True
                            if product_item_id:
                                # Get product sku
                                request = self.env['base.integrate.lazada']._get_data_lazada(url_api, payload)
                                if request.get('code') == '0':
                                    if request.get('data'):
                                        seller_product = request.get('data')
                                        if seller_product.get('skus'):
                                            for p in seller_product.get('skus'):
                                                if seller_sku_list == p.get('SellerSku'):
                                                    product_details[count].sudo().write({
                                                        's_lazada_seller_sku': p.get('SellerSku'),
                                                        's_lazada_sku_id': p.get('SkuId'),
                                                        's_lazada_is_mapped_product': True,
                                                        's_lazada_item_id': seller_product.get('item_id'),
                                                    })
                                        else:
                                            vals.update({
                                                's_product_id': product_details[count].id,
                                                'message': 'Không có seller_sku trong respone trả về'
                                            })
                                            sync_failed = True
                                    else:
                                        vals.update({
                                            's_product_id': product_details[count].id,
                                            'message': request.get('message')
                                        })
                                        sync_failed = True
                                else:
                                    vals.update({
                                        's_product_id': product_details[count].id,
                                        'message': request.get('message')
                                    })
                                    sync_failed = True
                        if sync_failed:
                            self.env['s.marketplace.mapping.product'].sudo().create(vals)
                        count += 1
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Lỗi đồng bộ sản phẩm Lazada',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
            })
