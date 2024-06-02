from odoo import fields, models, api
import time
from datetime import datetime
import pytz
import logging
_logger = logging.getLogger(__name__)
class SResPartnerOtp(models.Model):
    _name = 's.res.partner.otp'
    _order = 'create_date desc'

    phone_number = fields.Char(string='Số điện thoại khách hàng')
    zalo_otp = fields.Char(string='Mã OTP Zalo')
    sum_quantity_order_line = fields.Integer(string='Số lượng sản phẩm order line')
    resend = fields.Boolean(string='Resend')
    cid_order = fields.Char(string='CID Order')
    type_otp = fields.Selection(string='Type OTP', selection=[('pos', 'Pos'), ('m2', 'M2')])
    status_otp = fields.Selection(string='Status OTP', selection=[('success', 'Success'), ('error', 'Error')])
    message_otp = fields.Char(string='Message OTP')

    def validate_order(self, phone_number, zalo_otp):
        result = False
        # phone = self.env['sms.sms'].sudo().convert_vietnamese_phone_number(phone_number)
        phone = phone_number
        if phone:
            partner_otp = self.sudo().search(
                [('phone_number', '=', str(phone)), ('type_otp', '=', 'pos'), ('status_otp', '=', 'success'),
                 ('zalo_otp', '=', str(zalo_otp))], order='create_date desc', limit=1)
            _logger.info('start validate_order')
            _logger.info(partner_otp)
            _logger.info(zalo_otp)
            _logger.info('end validate_order')
            if partner_otp:
                user_tz = self.env.user.tz or pytz.utc
                tz = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone(user_tz)).replace(tzinfo=None)
                expired_time = tz - partner_otp.create_date
                hours, remainder = divmod(expired_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                minutes = minutes + seconds / 60
                if minutes <= 5:
                    result = True
        return result

    @api.model
    def check_screen_otp(self):
        context = self.env.context
        # phone_number = self.env['sms.sms'].sudo().convert_vietnamese_phone_number(context.get('phone_number'))
        phone_number = context.get('phone_number')
        cid_order = context.get('cid_order')
        search_otp = self.sudo().search(
            [('phone_number', '=', str(phone_number)), ('cid_order', '=', cid_order), ('type_otp', '=', 'pos'),
             ('status_otp', '=', 'success')],
            order='create_date desc', limit=1)
        _logger.info('start check_screen_otp')
        _logger.info(search_otp)
        _logger.info(cid_order)
        _logger.info(phone_number)
        _logger.info('end check_screen_otp')
        if not search_otp:
            return 0
        else:
            user_tz = self.env.user.tz or pytz.utc
            tz = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone(user_tz)).replace(tzinfo=None)
            expired_time = tz - search_otp.create_date
            hours, remainder = divmod(expired_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            minutes = minutes + seconds / 60
            if minutes < 5 and seconds < 60:
                seconds_remaining = 300 - (minutes * 60 + seconds)
                return str(seconds_remaining)
            else:
                return 0
