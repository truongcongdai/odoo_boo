from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class InforCustomer(models.TransientModel):
    _name = "logistic.mass.action.infor.receiver"

    s_infor_receiver = fields.Many2one('hr.employee', string='Người nhận hàng')
    s_logistic_ids = fields.Many2one('s.logistic.tracking', string='Mã phiếu điều chuyển')

    def s_submit_logistic_infor_receiver(self):
        if self.s_infor_receiver:
            self.s_logistic_ids = self._context.get('defaults_s_logistic_ids')
            if self.s_logistic_ids:
                self._cr.execute("""
                    UPDATE s_logistic_tracking set s_receiver = %s, s_state = %s WHERE id = %s""", (self.s_infor_receiver.id, 'delivered', self.s_logistic_ids.id,))
        else:
            raise ValidationError(_('Vui lòng chọn người nhận hàng!'))

