from odoo import models
import math, random
import logging
_logger = logging.getLogger(__name__)

class SSmsSmsInherit(models.Model):
    _inherit = 'sms.sms'

    def generate_otp(self):
        digits = '0123456789'
        otp_length = 6
        otp = ''
        for number in range(otp_length):
            otp += digits[math.floor(random.random() * 10)]
        return otp

    def convert_vietnamese_phone_number(self, phone_number):
        phone = phone_number.replace('0', '84', 1) if phone_number else ""
        return phone

    def send_otp_zns(self, phone_number, zalo_zns_template_id, cid_order, type_otp):
        # get opt
        otp = self.generate_otp()
        param_create_log_otp = {
            'phone_number': str(phone_number),
            'zalo_otp': str(otp),
            'cid_order': cid_order,
            'type_otp': type_otp,
        }
        # convert phone number to area
        phone_number = self.convert_vietnamese_phone_number(phone_number)
        template_id = self.env['zns.template'].sudo().search([('id', '=', zalo_zns_template_id)], limit=1)
        check_otp = False
        if template_id and phone_number and not check_otp:
            # send otp zns
            data = {
                "phone": str(phone_number),
                "template_id": str(template_id.s_template_id),
                "template_data": {
                    "otp": str(otp)
                },
                "tracking_id": str(otp)
            }
            zalo_mode = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_zalo.zalo_mode')
            if zalo_mode == 'sandbox':
                data['mode'] = 'development'
            zalo_result = self.s_send_data_zns(data=data)
            if zalo_result.get('state') == 'success':
                param_create_log_otp.update({
                    'status_otp': 'success',
                    'message_otp': 'Gửi mã OTP thành công'
                })
                _logger.info('start send_otp_zns')
                _logger.info(zalo_result)
                _logger.info(param_create_log_otp)
                _logger.info('end send_otp_zns')
                self.env['s.res.partner.otp'].sudo().create(param_create_log_otp)
                return otp
            else:
                param_create_log_otp.update({
                    'status_otp': 'error',
                    'message_otp': "Lỗi: " + str(zalo_result.get('message')) + " - " + "Param call: " + str(data)
                })
                self.env['s.res.partner.otp'].sudo().create(param_create_log_otp)
