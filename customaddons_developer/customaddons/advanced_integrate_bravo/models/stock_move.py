import json
import time
from datetime import datetime,timedelta
from odoo import fields, models, api
from odoo.http import request, _logger


class StockMove(models.Model):
    _inherit = ['stock.move']

    inventory_adjustment_quantity = fields.Float(
        string='Inventory Adj. Qty',
        readonly=True,
        help='This is a technical field, to store inventory adjustment qty after update action'
    )
    to_bravo = fields.Boolean(string="Đã đẩy sang Bravo")

    mapping_bravo_ids = fields.Many2many(
        comodel_name='bravo.stock.picking.mappings',
        string='Bravo Mappings',
    )

