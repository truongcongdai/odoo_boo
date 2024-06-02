from datetime import datetime, timedelta
from odoo import models, fields, api


class SPosOrder(models.Model):
    _inherit = 'pos.order'
    is_order_payment = fields.Boolean(string='Là đơn hàng đã thanh toán', compute='_pos_order_state', store=True)
    is_send_message = fields.Boolean(string='Là đơn hàng đã gửi tin nhắn', default=False)
    send_message_error = fields.Boolean(string='Gửi Zns lỗi', default=False)

    @api.depends('state')
    def _pos_order_state(self):
        for r in self:
            r.sudo().is_order_payment = False
            if r.state in ['paid', 'done', 'invoiced']:
                r.sudo().is_order_payment = True

    @api.model
    def create(self, vals):
        res = super(SPosOrder, self).create(vals)
        if res.partner_id and not res.partner_id.check_buy_order:
            res.partner_id.check_buy_order = True
        return res

    def write(self, vals):
        if vals.get('is_send_message'):
            for r in self:
                self._cr.execute(
                    """UPDATE pos_order SET is_send_message = %s WHERE id = %s""",
                    (vals.get('is_send_message'), r.id))
            vals.pop('is_send_message')
        else:
            return super(SPosOrder, self).write(vals)
