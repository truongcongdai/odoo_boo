from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    def unlink(self):
        partner = self.env.ref('advanced_integrate_bravo.s_res_partner_bravo')
        if partner:
            partner_id = partner.id
            for rec in self:
                if rec.id == partner_id:
                    raise ValidationError('Bản ghi không thể xóa!')
        return super(ResPartnerInherit, self).unlink()

    # def write(self, vals):
    #     partner = self.env.ref('advanced_integrate_bravo.s_res_partner_bravo')
    #     if partner:
    #         partner_id = partner.id
    #         for rec in self:
    #             if rec.id == partner_id:
    #                 raise ValidationError('Bản ghi không thể sửa/xóa')
    #     return super(ResPartnerInherit, self).write(vals)
