from odoo import fields, models, api, _


class SSaleOrderLoyaltyProgram(models.Model):
    _name = 's.sale.order.loyalty.program'

    name = fields.Char('Tên chương trình KHTT', required=True)
    s_points_quantity = fields.Float('Điểm cho mỗi đơn vị', required=True, default=1)
    s_points_currency = fields.Float('Điểm cho mỗi giá tiền', required=True, digits=(12, 6))
    is_sale_order = fields.Boolean('Active', readonly=True, default=True)
