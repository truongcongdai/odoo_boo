# -*- coding: utf-8 -*-
from odoo import http, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.http import request
import pytz
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token
from odoo.addons.advanced_integrate_magento.tools.common import invalid_response, valid_response
from odoo.http import Response
import ast
import json
from datetime import datetime


class AdvancedLoyaltyProgram(http.Controller):
    @validate_integrate_token
    @http.route(['/check-reward-points'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def check_reward_points_magento(self, *args, **kwargs):
        try:
            phone = kwargs.get('phone')
            if not phone:
                raise ValidationError("Thiếu param phone!")
            amount_total_api = kwargs.get('amount_total')
            if not int(amount_total_api):
                raise ValidationError("Thiếu param amount_total!")
            date_order_api = kwargs.get('date_order')
            if not date_order_api:
                raise ValidationError("Thiếu param date_order!")
            product_api_ids = list(eval(kwargs.get('product_ids')))
            if not product_api_ids:
                raise ValidationError("Thiếu param product_ids!")
            redeem_type = kwargs.get('redeem_type')
            if not redeem_type:
                raise ValidationError("Thiếu param redeem_type!")
            condition_type = kwargs.get('condition_type')
            if not condition_type:
                raise ValidationError("Thiếu param condition_type!")
            redeem_amount = kwargs.get('redeem_amount')
            if not redeem_amount:
                raise ValidationError("Thiếu param redeem_amount!")
            partner_id = request.env['res.partner'].sudo().search([('phone', '=', phone), ('type', '=', 'contact')],
                                                                  limit=1)
            loyalty_program_id = request.env['loyalty.program'].sudo().search([('is_apply_so', '=', True)], limit=1)
            if loyalty_program_id and partner_id:
                point, list_point, s_redeem_amount = 0, [], 0
                if loyalty_program_id.reward_ids:
                    if condition_type == 'percent':
                        rewards_type_percent = loyalty_program_id.reward_ids.filtered(
                            lambda r: r.s_type_exchange == "percent" and r.reward_type == "point")
                        if rewards_type_percent:
                            if len(rewards_type_percent) == 1:
                                rate = rewards_type_percent.s_reward_exchange_monetary / rewards_type_percent.s_reward_exchange_point
                                exchange_maximum = (int(amount_total_api) / 100 * rewards_type_percent.s_exchange_maximum) / rate
                                if int(redeem_amount) > exchange_maximum:
                                    raise ValidationError("Điểm quy đổi vượt quá giới hạn quy đổi!")
                                else:
                                    s_redeem_amount = int(redeem_amount) * rate
                            elif len(rewards_type_percent) > 1:
                                for reward in rewards_type_percent:
                                    rate = reward.s_reward_exchange_monetary / reward.s_reward_exchange_point
                                    exchange_maximum = (int(amount_total_api) / 100 * reward.s_exchange_maximum) / rate
                                    if int(redeem_amount) < exchange_maximum:
                                        list_point.append({
                                            "exchange_maximum": exchange_maximum,
                                            "rate": rate,
                                            "reward_id": reward.id,
                                        })
                                if len(list_point) > 0:
                                    max_point = max(list_point, key=lambda x: x['exchange_maximum'])
                                    if max_point:
                                        if max_point.get("exchange_maximum") > int(redeem_amount):
                                             s_redeem_amount = int(redeem_amount) * max_point.get("rate")
                                        else:
                                            raise ValidationError("Điểm quy đổi vượt quá giới hạn quy đổi!")
                                else:
                                    raise ValidationError("Không có quy đổi điểm thỏa mãn điều kiện đã setup!")
                        else:
                            raise ValidationError("Không tìm thấy loại quy đổi điểm!")
                    if condition_type == 'points':
                        rewards_type_number = loyalty_program_id.reward_ids.filtered(
                            lambda r: r.s_type_exchange == "number" and r.reward_type == "point")
                        if rewards_type_number:
                            if len(rewards_type_number) == 1:
                                if rewards_type_number.s_exchange_maximum > 0:
                                    rate = rewards_type_number.s_reward_exchange_monetary / rewards_type_number.s_reward_exchange_point
                                    if rewards_type_number.s_exchange_maximum < int(redeem_amount):
                                        raise ValidationError("Điểm quy đổi vượt quá giới hạn quy đổi!")
                                    else:
                                        if int(amount_total_api) > int(redeem_amount) * rate:
                                            s_redeem_amount = int(redeem_amount) * rate
                                        else:
                                            raise ValidationError("Điểm quy đổi vượt quá giá trị đơn hàng!")
                            elif len(rewards_type_number) > 1:
                                for reward in rewards_type_number:
                                    rate = reward.s_reward_exchange_monetary / reward.s_reward_exchange_point
                                    reduced_money = (int(redeem_amount) * rate)
                                    if int(redeem_amount) < reward.s_exchange_maximum:
                                        list_point.append({
                                            "reduced_money": reduced_money,
                                            "reward_id": reward.id,
                                            "s_exchange_maximum": reward.s_exchange_maximum,
                                        })
                                if len(list_point) > 0:
                                    list_point.sort(key=lambda x: (x['reduced_money'], x['s_exchange_maximum']), reverse=True)
                                    max_point = max(list_point, key=lambda x: x['reduced_money'])
                                    if max_point:
                                        reward_id = request.env['loyalty.reward'].sudo().browse(max_point.get('reward_id'))
                                        if reward_id.exists():
                                            if reward_id.s_exchange_maximum > 0:
                                                if reward_id.s_exchange_maximum < int(redeem_amount):
                                                    raise ValidationError("Điểm quy đổi vượt quá giới hạn quy đổi!")
                                                else:
                                                    if int(amount_total_api) > max_point.get('reduced_money'):
                                                        s_redeem_amount = max_point.get('reduced_money')
                                                    else:
                                                        raise ValidationError("Điểm quy đổi vượt quá giá trị đơn hàng!")
                                else:
                                    raise ValidationError("Không có quy đổi điểm thỏa mãn điều kiện đã setup!")
                        else:
                            raise ValidationError("Không tìm thấy loại quy đổi điểm!")
                point = s_redeem_amount
                if loyalty_program_id.zns_template_id:
                    request.env['sms.sms'].sudo().send_otp_zns(phone, loyalty_program_id.zns_template_id.id, None, 'm2')
                request.env['ir.logging'].sudo().create({
                    'name': 'api-check-reward-points-magento',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(kwargs),
                    'func': 'check_reward_points_magento',
                    'line': '0',
                })
                return point
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-check-reward-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'check_reward_points_magento',
                'line': '0',
            })
            return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)

    @validate_integrate_token
    @http.route(['/resent-otp-reward-points'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def resent_otp_reward_points_magento(self, *args, **kwargs):
        try:
            phone = kwargs.get('phone')
            if not phone:
                raise ValidationError("Thiếu param phone!")

            partner_id = request.env['res.partner'].sudo().search([('phone', '=', phone), ('type', '=', 'contact')],
                                                                  limit=1)
            loyalty_program_id = request.env['loyalty.program'].sudo().search([('is_apply_so', '=', True)], limit=1)
            if partner_id and loyalty_program_id:
                if loyalty_program_id.zns_template_id:
                    msg_result = request.env['sms.sms'].sudo().send_otp_zns(phone,
                                                                            loyalty_program_id.zns_template_id.id, None,'m2')
                    request.env['ir.logging'].sudo().create({
                        'name': 'api-resent-otp-reward-points-magento',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'INFO',
                        'path': 'url',
                        'message': str(kwargs),
                        'func': 'resent_otp_reward_points_magento',
                        'line': '0',
                    })
                    return True
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-resent-otp-reward-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'resent_otp_reward_points_magento',
                'line': '0',
            })
            return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)

    @validate_integrate_token
    @http.route(['/check-otp-reward-points'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def check_otp_reward_points_magento(self, *args, **kwargs):
        try:
            phone = kwargs.get('phone')
            if not phone:
                raise ValidationError("Thiếu param phone!")
            otp = kwargs.get('otp')
            if not otp:
                raise ValidationError("Thiếu param otp!")
            # phone_number = request.env['sms.sms'].sudo().convert_vietnamese_phone_number(phone)
            phone_number = phone
            s_res_partner_otp_id = request.env['s.res.partner.otp'].sudo().search(
                [('phone_number', '=', phone_number), ('zalo_otp', '=', otp), ('type_otp', '=', 'm2'), ('status_otp', '=', 'success')], order='create_date desc', limit=1)
            request.env['ir.logging'].sudo().create({
                'name': 'api-check-otp-reward-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(kwargs),
                'func': 'check_otp_reward_points_magento',
                'line': '0',
            })
            if not s_res_partner_otp_id:
                return False
            else:
                user_tz = request.env.user.tz or pytz.utc
                tz = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone(user_tz)).replace(tzinfo=None)
                expired_time = tz - s_res_partner_otp_id.create_date
                hours, remainder = divmod(expired_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                minutes = minutes + seconds / 60
                if minutes < 5 and seconds < 60:
                    return True
                else:
                    return False
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-resent-otp-reward-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'check_otp_reward_points_magento',
                'line': '0',
            })
            return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)
