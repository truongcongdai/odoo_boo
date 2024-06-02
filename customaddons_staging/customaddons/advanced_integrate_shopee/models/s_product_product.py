from odoo import fields, models, api
from odoo.exceptions import ValidationError, _logger
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
