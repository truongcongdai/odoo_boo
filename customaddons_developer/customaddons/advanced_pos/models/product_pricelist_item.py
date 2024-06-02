from odoo import fields, models, api
from datetime import datetime, timedelta


class SProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def _cron_delete_product_pricelist_expired(self):
        self.env['product.pricelist.item'].sudo().search([('date_end', '<=', fields.Datetime.now())]).unlink()
