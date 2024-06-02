from odoo.exceptions import ValidationError
from odoo import fields, api, models, tools
import urllib3

urllib3.disable_warnings()


class SProductTemplateLazada(models.Model):
    _inherit = 'product.template'
    _order = "list_price asc"
    s_lazada_item_id = fields.Char(
        string='Lazada Item ID',
        required=False)
