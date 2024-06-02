# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.phone_validation.tools import phone_validation


class MassSMSTest(models.TransientModel):
    _inherit = 'mailing.sms.test'
    _description = 'Test SMS Mailing'
    s_is_zalo_mailing_sms = fields.Boolean(string='Gửi qua Zalo', related="mailing_id.s_is_zalo_sms_marketing")

    def s_zalo_action_send_sms(self):
        self.ensure_one()

        numbers = [number.strip() for number in self.numbers.splitlines()]
        sanitize_res = phone_validation.phone_sanitize_numbers_w_record(numbers, self.env.user)
        sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
        invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]
        sent_sms_list = []
        # res_id is used to map the result to the number to log notifications as IAP does not return numbers...
        # TODO: clean IAP to make it return a clean dict with numbers / use custom keys / rename res_id to external_id
        if len(sanitized_numbers) > 0:
            if self.mailing_id and self.mailing_id.s_is_zalo_sms_marketing:
                for number in sanitized_numbers:
                    zalo_mode = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_zalo.zalo_mode')

                    data = {
                        "phone": number,
                        "template_id": self.mailing_id.s_zalo_zns_template_id.s_template_id,
                        "template_data": {
                            "customer_name": self.env.user.partner_id.name,
                            "company_name": self.env.company.name if self.env.company.name else '',
                        },
                        "tracking_id": self.id,
                    }
                    if zalo_mode == 'sandbox':
                        data['mode'] = 'development'
                    result = self.env['sms.sms'].s_send_data_zns(data)
                    result['number'] = number
                    sent_sms_list.append(result)
        notification_messages = []
        if invalid_numbers:
            notification_messages.append(_('The following numbers are not correctly encoded: %s',
                                           ', '.join(invalid_numbers)))
        for sent_sms in sent_sms_list:
            if sent_sms.get('state') == 'success':
                notification_messages.append(
                    _('Test SMS successfully sent to: %s', sent_sms['number']))
            elif sent_sms.get('state'):
                notification_messages.append(
                    _('Test SMS could not be sent to %s:<br>%s',
                      sent_sms.get('res_id'), sent_sms['message'])
                )

        if notification_messages:
            self.mailing_id._message_log(body='<ul>%s</ul>' % ''.join(
                ['<li>%s</li>' % notification_message for notification_message in notification_messages]
            ))

        return True
