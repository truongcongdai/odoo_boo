from odoo import fields, models, api


class MassInsertCouponProgram(models.TransientModel):
    _name = 'mass.insert.coupon.program'

    coupon_program_ids = fields.Many2many(comodel_name='coupon.program', string='Chương trình khuyến mãi')
    pos_ids = fields.Many2many(comodel_name='pos.config', string='Cửa hàng')

    def confirm_coupon_program(self):
        for pos in self.pos_ids:
            for coupon_program in self.coupon_program_ids:
                pos.write({'promo_program_ids': [(4, coupon_program.id)]})

