from odoo import fields, models, api
import time
import logging
_logger = logging.getLogger(__name__)

class CreateInventoryAdjustments(models.Model):
    _name = 's.create.inventory.adjustments'

    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Địa điểm')

    product_sku = fields.Char(
        string='Sản phẩm')
    quantity = fields.Integer(
        string='Số lượng',
        required=False)
    inventory_qty_set = fields.Boolean(
        string='Bộ số lượng tồn kho',
        required=False)

    def cron_apply_inventory(self):
        start_time = time.time()
        try:
            self._cr.execute("""SELECT id,location_id,product_sku,quantity,inventory_qty_set 
            FROM s_create_inventory_adjustments
            WHERE product_sku IN (SELECT default_code FROM product_product WHERE default_code is not null)""", )
            query_result = self.env.cr.dictfetchall()
            limit_inventory_adjustments = self.env['ir.config_parameter'].get_param(
                'advanced_inventory.limit_inventory_adjustments', 10)
            count = 0
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                for rec in query_result[:int(limit_inventory_adjustments)]:
                    if rec.get('product_sku'):
                        product_id = self.env['product.product'].sudo().search([('default_code', '=', rec.get('product_sku'))],
                                                                               limit=1)
                        if product_id:
                            stock_quant = self.env['stock.quant'].with_context(inventory_mode=True).sudo().create({
                                'product_id': product_id.id,
                                'inventory_quantity': rec.get('quantity'),
                                'location_id': rec.get('location_id'),
                            })
                            if stock_quant:
                                self.env['s.create.inventory.adjustments'].sudo().browse(rec.get('id')).unlink()
                                # if stock_quant.product_tmpl_id:
                                #     if stock_quant.product_tmpl_id.check_sync_product:
                                stock_quant.action_apply_inventory()
                                self.env.cr.commit()
        except Exception as ex:
            error = traceback.format_exc()
            _logger.error('cron_post_product_m2')
            _logger.error(error)

