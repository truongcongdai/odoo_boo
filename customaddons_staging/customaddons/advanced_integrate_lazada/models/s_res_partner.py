from odoo import fields, models, api, _
from odoo import api, models
from odoo.exceptions import ValidationError


class SLazadaResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    def unlink(self):
        partner = self.env.ref('advanced_integrate_lazada.customer_lazada')
        if partner:
            partner_id = partner.id
            for rec in self:
                if rec.id == partner_id:
                    raise ValidationError('Bản ghi %s không thể xóa!' % rec.name)
        return super(SLazadaResPartnerInherit, self).unlink()
