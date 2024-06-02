from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class SPosOrderPayment(models.Model):
    _inherit = 'pos.payment.method'

    payment_method_giftcard = fields.Boolean(string="Phương thức thanh toán Gift Card", default=False)

    @api.constrains('payment_method_giftcard')
    def payment_method_giftcard_only(self):
        payment_method_giftcard = self.env['pos.payment.method'].search([('payment_method_giftcard', '=', True)])
        if len(payment_method_giftcard) > 1:
            raise ValidationError('Không được phép tạo 2 phương thức thanh toán Giftcard')

    def write(self, vals):
        if self._is_write_forbidden(set(vals.keys())):
            raise UserError('Vui lòng đóng và xác thực các Phiên PoS mở sau đây trước khi sửa đổi phương thức thanh toán này.\n'
                            'Phiên đang mở: %s' % (' '.join(self.open_session_ids.mapped('name')),))
        return super(SPosOrderPayment, self).write(vals)
