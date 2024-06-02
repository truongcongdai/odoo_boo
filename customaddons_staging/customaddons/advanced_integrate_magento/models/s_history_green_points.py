from datetime import date

from odoo import models
from datetime import datetime


class SHistoryGreenPointsInherit(models.Model):
    _inherit = 's.history.green.points'

    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('res_partner_id') and vals.get('diem_cong'):
                today = date.today()
                partner_id = self.env['res.partner'].sudo().browse(vals.get('res_partner_id'))
                if partner_id:
                    self.env['s.customer.loyalty.points'].sudo().create({
                        "commercial_points": 0,
                        "commercial_points_comment": "",
                        "commercial_date": False,
                        "green_points": int(vals.get('diem_cong')),
                        "green_points_comment": "",
                        "green_date": vals.get('ngay_tich_diem'),
                        "partner_id": vals.get('res_partner_id'),
                        "type_points": "reward"
                    })
                # partner_id.push_data_customer(partner_id.phone, {
                #     "reward_points": {
                #         "commercial_points": 0,
                #         "commercial_points_comment": "",
                #         "commercial_date": "",
                #         "green_points": vals.get('diem_cong'),
                #         "green_points_comment": "",
                #         "green_date": vals.get('ngay_tich_diem'),
                #     }
                # }, 'updateRewardPoint')
        return super(SHistoryGreenPointsInherit, self).create(vals_list)

    def write(self, vals):
        if self.res_partner_id and vals.get('diem_cong'):
            diem_cong = vals.get('diem_cong') - self.diem_cong
            green_date = str(self.ngay_tich_diem)
            if self.res_partner_id:
                self.env['s.customer.loyalty.points'].sudo().create({
                    "commercial_points": 0,
                    "commercial_points_comment": "",
                    "commercial_date": False,
                    "green_points": int(diem_cong),
                    "green_points_comment": "",
                    "green_date": green_date,
                    "partner_id": self.res_partner_id.id,
                    "type_points": "reward"
                })
                # self.res_partner_id.push_data_customer(self.res_partner_id.phone, {
                #     "reward_points": {
                #         "commercial_points": 0,
                #         "commercial_points_comment": "",
                #         "commercial_date": "",
                #         "green_points": int(diem_cong),
                #         "green_points_comment": "",
                #         "green_date": green_date,
                #     }
                # }, 'updateRewardPoint')
        return super(SHistoryGreenPointsInherit, self).write(vals)

    def unlink(self):
        if self.res_partner_id and self.diem_cong:
            diem_cong = (-self.diem_cong)
            green_date = str(self.ngay_tich_diem)
            if self.res_partner_id:
                self.env['s.customer.loyalty.points'].sudo().create({
                    "commercial_points": 0,
                    "commercial_points_comment": "",
                    "commercial_date": False,
                    "green_points": int(diem_cong),
                    "green_points_comment": "",
                    "green_date": green_date,
                    "partner_id": self.res_partner_id.id,
                    "type_points": "reward"
                })
            # self.res_partner_id.push_data_customer(self.res_partner_id.phone, {
            #     "reward_points": {
            #         "commercial_points": 0,
            #         "commercial_points_comment": "",
            #         "commercial_date": "",
            #         "green_points": int(diem_cong),
            #         "green_points_comment": "",
            #         "green_date": green_date,
            #     }
            # }, 'updateRewardPoint')
        return super(SHistoryGreenPointsInherit, self).unlink()
