from odoo import fields, models, _
import json
from odoo.exceptions import ValidationError


class SShippingMethod(models.TransientModel):
    _name = "shipping.method"

    select_shipping_method = fields.Selection([("1", "Pick Up"), ("2", "Drop off")], string="Arrange Shipment")

    def btn_submit(self, context=None):
        package_id = self.env.context.get('active_id')
        package_tiktok_id = self.env['stock.picking'].search([('id', '=', package_id)],limit=1)
        package_tiktok_id.tiktok_shipping_method = self.select_shipping_method
        package_tiktok_id.is_selected_shipping_method = True
