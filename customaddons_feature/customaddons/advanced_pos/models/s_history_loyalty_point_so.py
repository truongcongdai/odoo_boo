from odoo import fields, models


class SHistoryLoyaltyPointSO(models.Model):
    _name = 's.history.loyalty.point.so'

    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng Online')
    res_partner_id = fields.Many2one('res.partner', string='Khách hàng')
    ly_do = fields.Char(string='Lý do cộng điểm')
    diem_cong = fields.Float(string='Điểm cộng')
