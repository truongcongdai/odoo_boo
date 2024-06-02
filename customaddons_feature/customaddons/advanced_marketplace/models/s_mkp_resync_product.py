import json
import ast
import time
from datetime import date, timedelta, datetime
from odoo.exceptions import ValidationError, _logger
from odoo import fields, models, api
from odoo.tests import Form


class SMarketPlaceResyncProduct(models.Model):
    _name = 's.mkp.resync.product'

    s_mkp_sku = fields.Char(string="SKU")
    s_mkp_ma_san_pham = fields.Char(string="Mã sản phẩm")

    def delete_the_recreated_record(self, product):
        if product.get('id'):
            delete_mkp_mapping_product = self._cr.execute(
                'delete from s_marketplace_mapping_product where id = ' + str(product.get('id')))

    def cronjob_resync_product(self, limit_search=False):
        count = 0
        start_time = time.time()
        if not limit_search:
            limit_search = 50
        lzd_skus = []
        lzd_product_ids = []
        # query_product = self._cr.execute(
        #     """select distinct a.*, b.id as id_resync from s_marketplace_mapping_product as a inner join s_mkp_resync_product as b on a.seller_sku = b.s_mkp_sku and b.s_mkp_sku is not NULL LIMIT %s""",
        #     (limit_search,))
        # product_ids = [item for item in self._cr.dictfetchall()]
        # query_template = self._cr.execute(
        #     """select a.*, s_mkp_resync_product.id as id_resync from s_marketplace_mapping_product as a, s_mkp_resync_product where a.s_template_id in (select b.id from product_template as b, s_mkp_resync_product as c where b.ma_san_pham = c.s_mkp_ma_san_pham and active = True) and s_mkp_resync_product.s_mkp_ma_san_pham is not NULL LIMIT %s""",
        #     (limit_search,))
        # template_ids = [item for item in self._cr.dictfetchall()]

        query = self._cr.execute(
            """select distinct * from s_mkp_resync_product as b where b.s_mkp_sku is not NULL LIMIT %s""",
            (limit_search,))
        result_query = [item for item in self._cr.dictfetchall()]

        # product_resync.extend(template_ids)
        if len(result_query) > 0:
            while (time.time() - start_time) <= 60 and count < len(result_query):
                product_resync = []
                if result_query[count].get('s_mkp_sku'):
                    query_product = self._cr.execute(
                        """select distinct a.* from s_marketplace_mapping_product as a inner join s_mkp_resync_product as b on a.seller_sku = %s LIMIT %s""",
                        (result_query[count].get('s_mkp_sku'), limit_search,))
                    product_ids = [item for item in self._cr.dictfetchall()]
                    product_resync.extend(product_ids)
                elif result_query[count].get('s_mkp_ma_san_pham'):
                    query_template = self._cr.execute(
                        """select distinct a.* from s_marketplace_mapping_product as a, s_mkp_resync_product where a.s_template_id in (select b.id from product_template as b, s_mkp_resync_product as c where b.ma_san_pham = %s and active = True) LIMIT %s""",
                        (result_query[count].get('s_mkp_ma_san_pham'), limit_search,))
                    template_ids = [item for item in self._cr.dictfetchall()]
                    product_resync.extend(template_ids)
                if len(product_resync) > 0:
                    for rec in product_resync:
                        if rec.get('s_error_type'):
                            s_error_type = rec.get('s_error_type')
                            if s_error_type == 'stock_error':
                                if rec.get('s_mapping_ecommerce') == 'shopee':
                                    self.env['s.marketplace.mapping.product'].sudo().resync_stock_product_shopee(rec)
                                    self.sudo().delete_the_recreated_record(rec)
                                    self._cr.execute(
                                        'delete from s_mkp_resync_product where id = ' + str(
                                            result_query[count].get('id')))
                                elif rec.get('s_mapping_ecommerce') == 'tiktok':
                                    self.env['s.marketplace.mapping.product'].sudo().resync_update_stock_product_tiktok(
                                        rec)
                                    self.sudo().delete_the_recreated_record(rec)
                                    self._cr.execute(
                                        'delete from s_mkp_resync_product where id = ' + str(
                                            result_query[count].get('id')))
                                elif rec.get('s_mapping_ecommerce') == 'lazada':
                                    search_product = self.env['product.product'].sudo().search(
                                        [('id', '=', rec.get('s_product_id'))], limit=1)
                                    if search_product.need_sync_lazada_stock:
                                        stock_quant_ids = int(sum(search_product.stock_quant_ids.filtered(
                                            lambda r: r.location_id.warehouse_id.is_push_lazada == True).mapped(
                                            "available_quantity")))
                                        value = {
                                            "ItemId": search_product.s_lazada_item_id,
                                            "SkuId": search_product.s_lazada_sku_id,
                                            "SellerSku": search_product.s_lazada_seller_sku,
                                            "SellableQuantity": stock_quant_ids
                                        }
                                        if search_product.is_merge_product == True:
                                            product_merge_ids = search_product.search(
                                                [('marketplace_sku', '=', search_product.marketplace_sku),
                                                 ('is_merge_product', '=', True), ('to_sync_lazada', '=', True)])
                                            quantity_available = product_merge_ids.stock_quant_ids.filtered(
                                                lambda r: r.location_id.warehouse_id.is_push_lazada == True).mapped(
                                                "available_quantity")
                                            value.update({"Quantity": sum(quantity_available)})
                                            value.update({"SellerSku": search_product.marketplace_sku})
                                        lzd_skus.append(value)
                                        lzd_product_ids.append(search_product)
                                    self.sudo().delete_the_recreated_record(rec)
                                    self._cr.execute(
                                        'delete from s_mkp_resync_product where id = ' + str(
                                            result_query[count].get('id')))
                            elif s_error_type == 'product_error':
                                if rec.get('s_mapping_ecommerce') == 'shopee':
                                    self.env['s.marketplace.mapping.product'].sudo().resync_product_shopee(rec)
                                    self.sudo().delete_the_recreated_record(rec)
                                    self._cr.execute('delete from s_mkp_resync_product where id = ' + str(
                                        result_query[count].get('id')))
                                elif rec.get('s_mapping_ecommerce') == 'tiktok':
                                    self.env['s.marketplace.mapping.product'].sudo().resync_product_tiktok(rec)
                                    self.sudo().delete_the_recreated_record(rec)
                                    self._cr.execute('delete from s_mkp_resync_product where id = ' + str(
                                        result_query[count].get('id')))
                count += 1
            if lzd_skus:
                self.env['s.marketplace.mapping.product'].sudo().resync_stock_product_lazada(lzd_skus, lzd_product_ids)
