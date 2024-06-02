from odoo import fields, models, api, _
from odoo import api, models
from odoo.exceptions import ValidationError


class SResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not name:
            partners = self.search(['|', ('name', operator, name), ('phone', operator, name),
                                    ], limit=10)
            return partners.name_get()
        else:
            partners = self.search(['|', ('name', operator, name), ('phone', operator, name)], limit=1000)
            return partners.name_get()
    def unlink(self):
        partner = self.env.ref('advanced_integrate_tiktok.s_res_partner_tiktok')
        if partner:
            partner_id = partner.id
            for rec in self:
                if rec.id == partner_id:
                    raise ValidationError('Bản ghi %s không thể xóa!' % rec.name)
        return super(SResPartnerInherit, self).unlink()
