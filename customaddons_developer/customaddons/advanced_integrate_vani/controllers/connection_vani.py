from odoo import http
from odoo.http import request
import json
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token
from odoo.addons.advanced_integrate_magento.tools.common import invalid_response


class ConnectionVani(http.Controller):
    @validate_integrate_token
    @http.route('/connection', type='json', auth='none', methods=['POST'], csrf=False)
    def connect(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data)
            customer = request.env['res.partner'].sudo()
            if not body.get('requestId'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "requestId is mandatory"}
            if not body.get('membershipId'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "membershipId is mandatory"}
            if not body.get('customerId'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "customerId is mandatory"}
            if not body.get('vanilaBarcode'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "vanilaBarcode is mandatory"}
            customer_id = customer.browse(int(body.get('customerId')))
            if not customer_id.exists():
                return {"api_vani": True, "message": "customerId may not exists or deleted!"}
            customer_id.write({
                'is_connected_vani': True,
                'vanila_barcode': body.get('vanilaBarcode'),
                'barcode': body.get('vanilaBarcode')
            })
            request.env['request.vani.history'].sudo().create({
                'request_id': body.get('requestId'),
                'vani_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/connection',
                'param': body
            })
            return {
                "api_vani": True,
                "customerId": str(customer_id.id),
                "membershipLevel": str(customer_id.customer_ranked),
                "membershipPoint": customer_id.loyalty_points,
            }
        except Exception as e:
            return invalid_response(head='provided_data_failures', message=e.args)
