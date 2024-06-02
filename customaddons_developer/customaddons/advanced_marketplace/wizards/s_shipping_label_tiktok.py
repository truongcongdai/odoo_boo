from odoo import fields, models, _
import json
from odoo.exceptions import ValidationError


class SShippingLabelTiktok(models.Model):
    _name = "shipping.label.tiktok"

    binary = fields.Binary()
    file_name = fields.Char(default="Shipping Label Tiktok")
    print_label_error = fields.One2many('shipping.label.error', 'shipping_label_id')