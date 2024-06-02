from odoo import fields, models


class SShippingLabelReport(models.TransientModel):
    _name = 'error.shipping.label.shopee'

    name = fields.Char(string='Mã đơn hàng')
    message = fields.Char(string='Lỗi')
    error_label = fields.Many2one('shipping.label.report.shopee')
