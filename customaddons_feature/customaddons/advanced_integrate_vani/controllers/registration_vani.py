from odoo import http
from odoo.http import request
import json
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token
import re
from werkzeug.exceptions import NotFound


# API registration Vani


class RegistrationVani(http.Controller):
    @validate_integrate_token
    @http.route('/registration', type='json', auth='none', methods=["POST"], csrf=False)
    def register(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data)
            if not body.get('requestId'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "requestId is mandatory"}
            if not body.get('membershipId'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "membershipId is mandatory"}
            if not body.get('mobilePhoneNo'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "mobilePhoneNumber is mandatory"}
            if not body.get('dateOfBirth'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "dateOfBirth is mandatory"}
            if not body.get('gender'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "gender is mandatory"}
            if not body.get('customerName'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "customerName is mandatory"}
            if not body.get('vanilaBarcode'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "vanilaBarcode is mandatory"}
            if not body.get('addressDetailInfo')['state']:
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "state is mandatory"}
            if not body.get('addressDetailInfo')['district']:
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "district is mandatory"}
            if not body.get('addressDetailInfo')['detail1']:
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "detail1 is mandatory"}
            if not body.get('addressDetailInfo')['detail2']:
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "detail2 is mandatory"}

            # Kiểm tra định dạng email
            check_email_format = re.match('^[_A-Za-z0-9-]+(\.[_a-za-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                                          body.get('emailAddress'))
            if body.get('emailAddress'):
                if not check_email_format:
                    return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                            "errorMessage": "Wrong email format"}

            # Kiểm tra định dạng số điện thoại di động
            check_phone_format = re.match('^[0-9]\d{9}$', body.get('mobilePhoneNo'))
            if body.get('mobilePhoneNo'):
                if not check_phone_format:
                    return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                            "errorMessage": "Wrong mobile phone format"}

            # Kiểm tra định dạng ngày sinh
            check_date_format = re.compile(r'^\d{4}-\d{2}-\d{2}$')
            if body.get('dateOfBirth'):
                if not check_date_format.match(body.get('dateOfBirth')):
                    return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "Wrong date format"}

            # Kiểm tra định dạng Vanila Barcode
            check_vanila_barcode = body.get('vanilaBarcode').isdigit()
            if len(body.get('vanilaBarcode')) == 16:
                if check_vanila_barcode is False:
                    return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                            "errorMessage": "Wrong vanila barcode format"}
            else:
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "Wrong vanila barcode format"}
            values = {
                'membership_id': body.get('membershipId'),
                'phone': body.get('mobilePhoneNo'),
                'birthday': body.get('dateOfBirth'),
                'name': body.get('customerName'),
                'email': body.get('emailAddress'),
                'vanila_barcode': body.get('vanilaBarcode'),
                'barcode': body.get('vanilaBarcode'),
                'contact_address_complete': body.get('addressDetailInfo'),
                'is_connected_vani': True,
            }
            # Kiểm tra định dạng giới tính
            if body.get('gender'):
                if body.get('gender') == 'M':
                    values.update({
                        'gender': 'male',
                    })
                elif body.get('gender') == 'F':
                    values.update({
                        'gender': 'female',
                    })
                else:
                    return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                            "errorMessage": "Wrong gender format"}
            addressDetailInfo = body.get('addressDetailInfo')
            if addressDetailInfo:
                if addressDetailInfo.get('state'):
                    state_id = request.env['res.country.state'].sudo().search(
                        [('name', 'ilike', '%' + addressDetailInfo.get('state') + '%')],
                        limit=1)
                    if state_id:
                        values.update({
                            'state_id': state_id.id if state_id else False,
                        })
                    else:
                        values.update({
                            'city': addressDetailInfo.get('state'),
                        })
                if addressDetailInfo.get('district'):
                    district_id = request.env['res.country.address'].sudo().search(
                        [('name_with_type', 'ilike', addressDetailInfo.get('district')), ('type', '=', '1_province')],
                        limit=1)
                    if district_id:
                        values.update({
                            'district_id': district_id.id if district_id else False,
                        })
                    else:
                        values.update({
                            'district': addressDetailInfo.get('district'),
                        })
                if addressDetailInfo.get('detail1'):
                    ward_id = request.env['res.country.address'].sudo().search(
                        [('name_with_type', 'ilike', addressDetailInfo.get('detail1')),
                         ('type', 'not in', ['1_city', '1_province'])],
                        limit=1)
                    if ward_id:
                        values.update({
                            'ward_id': ward_id.id if ward_id else False,
                        })
                    else:
                        values.update({
                            'street2': addressDetailInfo.get('detail1'),
                        })
                if addressDetailInfo.get('detail2'):
                    street = addressDetailInfo.get('detail2')
                    if street:
                        values.update({
                            'street': street if street else False,
                        })

            phone_result = request.env['res.partner'].sudo().search(
                [('phone', '=', body.get('mobilePhoneNo')), ('type', '=', 'contact')], limit=1)
            if len(phone_result) > 0:
                # values.pop('vanila_barcode')
                # values.pop('barcode')
                # values.pop('is_connected_vani')
                # values.pop('membership_id')
                # Nếu đã tồn tại khách hàng thì update thông tin khách hàng theo param vani
                if phone_result.is_regis_vani:
                    values.pop('vanila_barcode')
                    values.pop('barcode')
                    values.pop('is_connected_vani')
                    values.pop('membership_id')
                    # Nếu đã tồn tại khách hàng thì update thông tin khách hàng theo param vani
                    phone_result.sudo().write(values)
                    # Báo lỗi đăng ký thành viên khi có thành viên đăng ký bằng số điện thoại đã tồn tại
                    return {"api_vani": True, "errorCode": "DUP_PHONE",
                            "errorMessage": "The phone number already exists"}
                    # Response.status = "400 Bad Request"
                else:
                    values.update({
                        'is_regis_vani': True,
                    })
                    phone_result.sudo().write(values)
            else:
                values.update({
                    'is_regis_vani': True,
                })
                request.env['res.partner'].sudo().create(values)
            request.env['request.vani.history'].sudo().create({
                'request_id': body.get('requestId'),
                'vani_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/registration',
                'param': body
            })
            phone_final_result = request.env['res.partner'].sudo().search(
                [('phone', '=', body.get('mobilePhoneNo')),('is_regis_vani', '=', True), ('type', '=', 'contact')], limit=1)
            return {
                "api_vani": True,
                "customerId": str(phone_final_result.id),
                "membershipLevel": str(phone_final_result.customer_ranked),
                "membershipPoint": phone_final_result.loyalty_points
            }
        except Exception as e:
            # return http.Response(status=404)
            raise NotFound('error message')
