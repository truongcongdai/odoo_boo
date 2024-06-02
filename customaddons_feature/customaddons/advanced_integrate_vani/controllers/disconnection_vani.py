from odoo import http
from odoo.http import request
import json
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token
from odoo.addons.advanced_integrate_magento.tools.common import invalid_response


class DisconnectVani(http.Controller):
    @validate_integrate_token
    @http.route('/disconnection', type='json', auth='none', methods=["POST"], csrf=False)
    def disconnect(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data)
            customer_id = request.env['res.partner'].sudo()
            if not body.get('customerId'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "customerId is mandatory"}
            if not body.get('vanilaBarcode'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER",
                        "errorMessage": "vanilaBarcode is mandatory"}
            if not body.get('reason'):
                return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "reason is mandatory"}
            customer_check_id = customer_id.browse(int(body.get('customerId')))
            if not customer_check_id.exists():
                return {"api_vani": True, 'message': 'customerId may not exists or deleted!'}
            customer_check_vanilaBarcode = customer_id.search([('vanila_barcode', '=', body.get('vanilaBarcode'))])
            if not customer_check_vanilaBarcode:
                return {"api_vani": True, 'message': 'vanilaBarcode may not exists or deleted!'}
            customer_id = customer_check_vanilaBarcode.search([('id', '=', int(body.get('customerId')))])
            if customer_id:
                if customer_id.is_connected_vani:
                    customer_id.sudo().write({
                        'is_connected_vani': False,
                        'barcode': None,
                        'vanila_barcode': None,
                    })
                return {"api_vani": True, "status": 'Disconnected!'}
        except Exception as e:
            return invalid_response(head='provided_data_failures', message=e.args)
