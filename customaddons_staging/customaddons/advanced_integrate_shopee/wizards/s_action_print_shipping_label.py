from odoo import _, api, fields, models


class SShippingLabelReport(models.Model):
    _name = 'shipping.label.report.shopee'

    binary_data = fields.Binary()
    file_name = fields.Char(string='Shipping Label Shopee', default='Shipping Label Shopee')
    failed_print_label = fields.One2many('error.shipping.label.shopee', 'error_label')
