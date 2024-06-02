from odoo import fields, models


class ImportCouponCouponInherit(models.TransientModel):
    _name = 'mass.import.coupon.coupon'
    s_import_coupon_coupon_ids = fields.Many2many('s.import.coupon.coupon', string='Coupon')

    def action_import_coupon(self):
        for rec in self:
            if len(rec.s_import_coupon_coupon_ids) > 0:
                for coupon in rec.s_import_coupon_coupon_ids:
                    self.env['coupon.coupon'].sudo().create({
                        'boo_code': coupon.boo_code,
                        'program_id': coupon.program_id.id,
                    })
        return self.s_import_coupon_coupon_ids.unlink()
