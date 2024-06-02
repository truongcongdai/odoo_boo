from odoo import http
from odoo.http import request
import json
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token

# API detail-info-search Vani


class DetailInfoSearchVani(http.Controller):
    @validate_integrate_token
    @http.route('/detail-info-search', type='json', auth='none', methods=['POST'], csrf=False)
    def detail_info_search(self, **kwargs):
        body = json.loads(request.httprequest.data)
        if not body.get('customerId'):
            return {"api_vani": True, "errorCode": "INSUFFICIENT_PARAMTER", "errorMessage": "customerId is mandatory"}
        customer_id_odoo = request.env['res.partner'].sudo().search([('id', '=', int(body.get('customerId')))])

        if customer_id_odoo:
            request.env['request.vani.history'].sudo().create({
                'request_id': body.get('requestId'),
                'vani_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/detail-info-search',
                'param': body
            })
            return {
                "api_vani": True,
                "membershipLevel": str(customer_id_odoo.customer_ranked),
                "availablePoint": customer_id_odoo.loyalty_points
            }
