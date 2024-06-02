from odoo import fields, models, api


class LazadaSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    lazada_reverse_status = fields.Char(string='Lazada reverse status')
