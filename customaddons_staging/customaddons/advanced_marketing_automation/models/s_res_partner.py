from odoo import fields, models, api
from datetime import datetime, date


class SResPartner(models.Model):
    _inherit = 'res.partner'

    is_birthday = fields.Boolean(string='Đến ngày sinh nhật')
    month = fields.Integer('Tháng')
    day = fields.Integer('Ngày')
    date_not_buy = fields.Integer("Số ngày chưa mua hàng")
    check_buy_order = fields.Boolean('Kiểm tra trạng thái mua hàng của KH', default=False)
    @api.onchange('birthday')
    def get_date_month(self):
        if self.birthday:
            date = datetime.strptime(str(self.birthday), "%Y-%m-%d")
            self.month = date.month
            self.day = date.day

    def cronjob_last_update_buy(self):
        partner_ids = self.sudo().search([('last_order', '!=', False), ('type', '=', 'contact'),
                                          ('check_buy_order', '=', True)])
        if partner_ids:
            for r in partner_ids:
                total_days = (fields.Datetime.now() - r.last_order).days
                self._cr.execute("""UPDATE res_partner SET date_not_buy = %s, check_buy_order = False 
                WHERE id = %s""", (total_days, r.id))

    def cronjob_is_birthday(self):
        query = """ UPDATE res_partner 
                    SET is_birthday= (CASE WHEN DATE_PART('day', res_partner.birthday) = DATE_PART('day', CURRENT_DATE) 
                    AND DATE_PART('month', res_partner.birthday) = DATE_PART('month', CURRENT_DATE) THEN TRUE ELSE FALSE END), 
                        day =(DATE_PART('day', res_partner.birthday)),
                        month =(DATE_PART('month', res_partner.birthday)) WHERE res_partner.birthday is not NULL AND res_partner.type = 'contact'"""
        self.env.cr.execute(query)

    @api.onchange('birthday')
    def _onchange_is_birthday(self):
        for rec in self:
            rec.is_birthday = False
            if rec.birthday:
                today = date.today()
                if today.day == rec.birthday.day and today.month == rec.birthday.month:
                    rec.is_birthday = True
