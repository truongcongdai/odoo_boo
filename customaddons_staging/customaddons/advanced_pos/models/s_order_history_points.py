from odoo import fields, models, api


class SOrderHistoryPoints(models.Model):
    _name = 's.order.history.points'
    _description = 'Lịch sử tích điểm'

    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng Online')
    invoice_id = fields.Many2one('account.move', string='Hóa đơn SO Online')
    order_id = fields.Many2one('pos.order', string='Đơn hàng POS')
    diem_cong = fields.Integer(string='Điểm cộng')
    ly_do = fields.Char(string='Lý do')
    res_partner_id = fields.Many2one('res.partner', string='Khách hàng')
    is_bill = fields.Boolean(string='Điểm cộng không lấy bill', default=False)
