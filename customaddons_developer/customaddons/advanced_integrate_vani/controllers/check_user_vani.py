from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token
from odoo import http
from odoo.http import request, Response, JsonRequest
import json
from odoo.tools import date_utils
from werkzeug.exceptions import NotFound


class CheckUserVani(http.Controller):
    @validate_integrate_token
    @http.route('/check-user', type='json', auth='none', methods=["POST"], csrf=False)
    def check_user(self, **kwargs):
        body = json.loads(request.httprequest.data)
        if not body.get('membershipId'):
            return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "membershipId is mandatory"}
        if not body.get('matchingType'):
            return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "matchingType is mandatory"}
        if not body.get('matchingValue'):
            return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                    "errorMessage": "matchingValue is mandatory"}
        if not body.get('dateOfBirth'):
            return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "dateOfBirth is mandatory"}
        check_user = request.env['res.partner'].sudo().search(
            [('phone', '=', body.get('matchingValue')), ('is_regis_vani', '=', True), ('type', '=', 'contact')],
            limit=1)
        if check_user:
            # Thay thế ngày sinh khách hàng bằng dateOfBirth của bên Vani
            check_user.write({
                'birthday': body.get('dateOfBirth'),
            })
            if check_user.gender == 'male':
                gender = 'M'
            elif check_user.gender == 'female':
                gender = 'F'
            else:
                gender = 'U'

            return {
                "api_vani": True,
                "customerInfoList": [
                    {
                        "customerId": str(check_user.id),
                        "customerName": check_user.name,
                        "gender": gender,
                        "brandBarcode": str(check_user.id),
                    }
                ]
            }
        else:
            raise NotFound('error message')
