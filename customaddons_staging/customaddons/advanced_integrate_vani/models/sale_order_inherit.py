from odoo import fields, models, api


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'
    is_vani_scan_barcode = fields.Boolean(
        string='Vani Barcode',
        required=False)
    is_vani_post_transaction = fields.Boolean(string='Vanila kiểm tra đơn hàng có được đẩy transaction qua Vani không')