from odoo import fields, models, api


class SCustomerLoyaltyPoints(models.Model):
    _name = 's.customer.loyalty.points'

    current_points = fields.Float(string='Điểm hiện tại của khách hàng')
    green_points = fields.Float(string='Điểm green hiện tại của khách hàng')
    commercial_points = fields.Float(string='Điểm commercial hiện tại của khách hàng')
    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    commercial_points_comment = fields.Char(string='Lý do điểm commercial')
    commercial_date = fields.Date(string='Ngày điểm commercial')
    green_points_comment = fields.Char(string='Lý do điểm green')
    green_date = fields.Date(string='Ngày điểm green')
    type_points = fields.Selection([('reward', 'updateRewardPoint'), ('current', 'updateCurrentPoint')],
                                   string='Loại điểm')
