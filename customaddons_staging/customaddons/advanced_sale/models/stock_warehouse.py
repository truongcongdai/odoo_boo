from odoo import fields, models, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    pos_config_ids = fields.One2many('pos.config', 'warehouse_id_related')