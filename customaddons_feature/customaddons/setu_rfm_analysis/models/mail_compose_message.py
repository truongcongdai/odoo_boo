from odoo import api, fields, models, tools


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def get_mail_values(self, res_ids):
        self.ensure_one()
        res = super(MailComposeMessage, self).get_mail_values(res_ids)
        segment = self.mass_mailing_id and self.mass_mailing_id.rfm_segment_id or False
        # use only for allowed models in mass mailing
        if segment and self.composition_mode == 'mass_mail' and \
                (self.mass_mailing_name or self.mass_mailing_id) and \
                self.env['ir.model'].sudo().search([('model', '=', self.model), ('is_mail_thread', '=', True)], limit=1):
            for res_id in res_ids:
                mail_values = res[res_id]
                email_from = mail_values and mail_values.get('email_from')
                if email_from:
                    # author_id, email_from = self.env['mail.thread']._message_compute_author(mail_values.get('author_id'), email_from, raise_exception=False)
                    mail_values.update({
                        'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from, records=None)[False],
                        'message_id': tools.generate_tracking_message_id('message-notify')
                    })
        return res
