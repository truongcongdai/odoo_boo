from odoo.exceptions import UserError, ValidationError
from odoo import fields, api, models
import requests
import json


class SStockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    e_commerce = fields.Selection([], string="Đồng bộ lên sàn TMĐT")