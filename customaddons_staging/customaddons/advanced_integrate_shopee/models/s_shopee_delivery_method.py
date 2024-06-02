import json
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class SShopeeDeliveryMethod(models.Model):
    _name = "s.shopee.delivery.method"

    shipping_method_shopee = fields.Selection([('pickup', 'Lấy hàng'), ('dropoff', 'Tự mang hàng ra bưu cục')],
                                              default='pickup', string='Phương thức nhận hàng Shopee')
    picking_id = fields.Many2one('stock.picking', string='Delivery Order')

    def action_push_delivery_method_shopee(self):
        picking_id = self.env.context.get('picking_id')
        package_shopee_id = self.env['stock.picking'].search([('id', '=', picking_id)], limit=1)
        package_shopee_id.shopee_shipping_method = self.shipping_method_shopee
        package_shopee_id.is_selected_shipping_method = True
