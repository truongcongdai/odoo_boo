from odoo import fields, models, api


class MailingTraceInherit(models.Model):
    _inherit = 'mailing.trace'
    s_zalo_state_msg = fields.Char(string='Lỗi Zalo')
    s_zalo_msg_id = fields.Char(string='ID Message Zalo')
    s_done_repeat = fields.Boolean(string='Tin nhắn đã gửi lại', default=False)