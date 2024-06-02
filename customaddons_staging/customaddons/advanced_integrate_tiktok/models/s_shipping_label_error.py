from odoo import fields, models, _
import json
from odoo.exceptions import ValidationError


class SShippingLabelTiktok(models.Model):
    _name = "shipping.label.error"

    name = fields.Char()
    message_error = fields.Char(string="Lỗi shipping label Tiktok")
    shipping_label_id = fields.Many2one('shipping.label.tiktok')