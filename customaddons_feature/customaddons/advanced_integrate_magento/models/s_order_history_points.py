from datetime import date

from odoo import models


class SOrderHistoryPointsInherit(models.Model):
    _inherit = 's.order.history.points'

    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('res_partner_id'):
                today = date.today()
                partner_id = self.env['res.partner'].sudo().browse(vals.get('res_partner_id'))
                if partner_id:
                    self.env['s.customer.loyalty.points'].sudo().create({
                        "commercial_points": vals.get('diem_cong'),
                        "commercial_points_comment": vals.get('ly_do'),
                        "commercial_date": str(today),
                        "green_points": 0,
                        "green_points_comment": "",
                        "green_date": False,
                        "partner_id": vals.get('res_partner_id'),
                        "type_points": "reward"
                    })
                # partner_id.push_data_customer(partner_id.phone, {
                #     "reward_points": {
                #         "commercial_points": vals.get('diem_cong'),
                #         "commercial_points_comment": vals.get('ly_do'),
                #         "commercial_date": str(today),
                #         "green_points": 0,
                #         "green_points_comment": "",
                #         "green_date": "",
                #     }
                # }, 'updateRewardPoint')
        return super(SOrderHistoryPointsInherit, self).create(vals_list)
