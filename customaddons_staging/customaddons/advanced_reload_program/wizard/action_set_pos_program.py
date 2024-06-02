from odoo import fields, models


class ActionSetPosProgram(models.TransientModel):
    _name = 'action.set.pos.program'

    program_ids = fields.Many2many('coupon.program', 'action_set_pos_promotion_program', string="Chương trình khuyến mãi")
    coupon_ids = fields.Many2many('coupon.program', 'action_set_pos_coupon_program', string="Chương trình phiếu giảm giá")
    pos_config_id = fields.Many2one('pos.config')

    def action_confirm(self):
        if self.pos_config_id:
            s_coupon_domain = ''
            s_promo_domain = ''
            if self.coupon_ids:
                domain1 = [["id", "in", self.coupon_ids.ids], ["program_type", "=", "coupon_program"]]
                domain1_dict = {"domain": domain1}
                s_coupon_domain = str(domain1_dict)
            if self.program_ids:
                domain2 = [["id", "in", self.program_ids.ids], ["program_type", "=", "promotion_program"]]
                domain2_dict = {"domain": domain2}
                s_promo_domain = str(domain2_dict)
            self.pos_config_id.sudo().write({
                's_coupon_domain': s_coupon_domain,
                's_promo_domain': s_promo_domain,
            })
