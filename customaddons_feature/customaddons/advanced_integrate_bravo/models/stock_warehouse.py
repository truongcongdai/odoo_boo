from odoo import models,fields,api
from odoo.exceptions import ValidationError


class StockWarehouseInherit(models.Model):
    _inherit = 'stock.warehouse'
    is_test_location = fields.Boolean(string="không đồng bộ dữ liệu Kho lên bravo")
    is_location_online = fields.Boolean(string="Là kho hàng online", default=False)

    @api.constrains('is_location_online')
    def _contrains_location_online(self):
        search_count_location_online = self.env['stock.warehouse'].sudo().search_count([('is_location_online', '=', True)])
        if search_count_location_online > 1:
            raise ValidationError('Kho hàng online là duy nhất')
