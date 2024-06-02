from odoo import fields, models, api


class SHistoryGreenPoints(models.Model):
    _name = 's.history.green.points'
    _description = 'Tích điểm khi mang đồ cũ tới đổi'

    ngay_tich_diem = fields.Date(string='Ngày tích điểm', required=True, default=fields.Date.today())
    diem_cong = fields.Integer(string='Điểm cộng', required=True, default=0)
    res_partner_id = fields.Many2one('res.partner', string='Khách hàng', required=True)

    @api.model
    def create(self, vals_list):
        res = super(SHistoryGreenPoints, self).create(vals_list)
        if vals_list.get('diem_cong'):
            res.res_partner_id.loyalty_points += vals_list.get('diem_cong')
        return res

    def write(self, vals_list):
        if vals_list.get('diem_cong'):
            self.res_partner_id.loyalty_points = self.res_partner_id.loyalty_points - self.diem_cong + vals_list.get('diem_cong')
        return super(SHistoryGreenPoints, self).write(vals_list)

    def unlink(self):
        if self.diem_cong:
            self.res_partner_id.loyalty_points -= self.diem_cong
        return super(SHistoryGreenPoints, self).unlink()
