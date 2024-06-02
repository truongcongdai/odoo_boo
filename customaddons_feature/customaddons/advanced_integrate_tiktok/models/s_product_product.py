from odoo import models, fields, api


class SProductProductInherit(models.Model):
    _inherit = 'product.product'

    # s_combine_product = fields.Boolean(string='Gộp sản phẩm trên Marketplace')
    id_skus = fields.Char('ID sản phẩm biến thể Tiktok')
    # general_default_code = fields.Char('General Sku')
    is_synced_tiktok = fields.Boolean('Đã đồng bộ sản phẩm lên tiktok', default=False, tracking=True)
    to_sync_tiktok = fields.Boolean('Đồng bộ Tiktok', default=False, tracking=True)
    need_sync_tiktok_stock = fields.Boolean('Cần đồng bộ tồn kho lên sàn tiktok', tracking=True)

    @api.onchange('to_sync_tiktok')
    def _constrains_delete_mapping_product_tiktok(self):
        updated_product_product_ids = []
        for rec in self:
            if not rec.to_sync_tiktok:
                updated_product_product_ids.append(rec._origin.id)
        if len(updated_product_product_ids) > 0:
            product_domain_list = [str(e) for e in updated_product_product_ids]
            product_domain_str = '(' + ','.join(product_domain_list) + ')'
            if '(False)' not in product_domain_str:
                self._cr.execute(
                    'update product_product set  is_synced_tiktok = FALSE, id_skus = null where id in ' + product_domain_str)
