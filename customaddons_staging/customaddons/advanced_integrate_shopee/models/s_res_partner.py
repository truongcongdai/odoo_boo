from odoo import fields, models, api, _
from odoo import api, models
from odoo.exceptions import ValidationError


class SShopeeResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    def unlink(self):
        partner = self.env.ref('advanced_integrate_shopee.s_res_partner_shopee')
        if partner:
            partner_id = partner.id
            for rec in self:
                if rec.id == partner_id:
                    raise ValidationError('Bản ghi %s không thể xóa!' % rec.name)
        return super(SShopeeResPartnerInherit, self).unlink()
