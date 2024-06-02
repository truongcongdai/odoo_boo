# -*- coding: utf-8 -*-
from datetime import datetime as dt
import logging
from odoo import http, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.http import request
from ..tools.api_wrapper import validate_integrate_token, _create_log
from ..tools.common import invalid_response
from .sale_order_controller import _get_partner_id

_logger = logging.getLogger(__name__)


class AdvancedIntegrateCustomerMagento(http.Controller):
    @validate_integrate_token
    @http.route(['/customer-create'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def create_res_partner(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            customer_result = _get_partner_id(body, api_customer=True)
            customer_id = customer_result['partner_id']
            if not customer_id:
                raise ValidationError('Customer may not exists or deleted!')
            customer = request.env['res.partner'].sudo().browse(customer_id)
            request.env['ir.logging'].sudo().create({
                'name': 'api-customer-create-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(body) if body else None,
                'func': 'create_res_partner',
                'line': '0',
            })
            return customer.read(
                ['name', 'phone', 'street', 'state_id', 'district_id', 'ward_id', 'customer_ranked', 'loyalty_points'])
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-customer-create-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'create_res_partner',
                'line': '0',
            })
            return invalid_response(head='create_customer_data_failures', message=e.args)

    @validate_integrate_token
    @http.route(['/customer-update'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def update_res_partner(self, *args, **kwargs):
        try:
            body = request.jsonrequest
            customer_result = _get_partner_id(body, api_customer=True)
            customer_id = customer_result['partner_id']
            if not customer_id:
                raise ValidationError('Customer may not exists or deleted!')
            customer = request.env['res.partner'].sudo().browse(customer_id)
            request.env['ir.logging'].sudo().create({
                'name': 'api-customer-update-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(body) if body else None,
                'func': 'update_res_partner',
                'line': '0',
            })
            return customer.read(['name', 'phone', 'street', 'state_id', 'district_id', 'ward_id', 'customer_ranked', 'loyalty_points'])

        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-customer-update-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(request.jsonrequest),
                'func': 'update_res_partner',
                'line': '0',
            })
            return invalid_response(head='update_customer_data_failures', message=e.args)

    @staticmethod
    def _format_hostory_loyalty_point(history_points_ids, history_so_points_ids, history_green_points_ids):
        history_point_obj = []
        history_green_point_obj = []
        for history_point_id in history_points_ids.sudo():
            history_point_obj.append({
                'id': history_point_id.id,
                'pos_order_id': history_point_id.order_id.id,
                'sale_order_id': history_point_id.sale_order_id.id,
                'diem_cong': history_point_id.diem_cong,
                'ly_do': history_point_id.ly_do,
            })
        for history_so_points_id in history_so_points_ids.sudo():
            history_point_obj.append({
                'id': history_so_points_id.id,
                'pos_order_id': False,
                'sale_order_id': history_so_points_id.sale_order_id.id,
                'diem_cong': history_so_points_id.diem_cong,
                'ly_do': history_so_points_id.ly_do,
            })
        for history_green_points_id in history_green_points_ids.sudo():
            history_green_point_obj.append({
                'id': history_green_points_id.id,
                'ngay_tich_diem': history_green_points_id.ngay_tich_diem,
                'diem_cong': history_green_points_id.diem_cong,
            })
        return {
            'history_point_obj': history_point_obj,
            'history_green_point_obj': history_green_point_obj
        }

    @validate_integrate_token
    @http.route('/history-loyalty-points', methods=['GET'], auth='public', type='json', csrf=False)
    def get_history_loyalty_point(self, *args, **kwargs):
        try:
            partner_result = _get_partner_id(kwargs, create=False)
            if not partner_result:
                raise ValidationError('Customer does not exits!')
            elif int(partner_result):
                partner_id = partner_result
            else:
                partner_id = partner_result.get('partner_id')

            partner_obj = request.env['res.partner'].sudo()
            if partner_id:
                partner_obj = partner_obj.browse(partner_id)
            if not partner_obj.exists() or not partner_obj.pos_order_ids:
                return {}
            limit = int(kwargs.get('limit'))
            page = int(kwargs.get('page'))
            loyalty_point_start_index = int(limit/3 * (page - 1))
            loyalty_point_end_index = int(limit/3 * page)
            history_points_ids = partner_obj.history_points_ids[loyalty_point_start_index:loyalty_point_end_index]
            history_so_points_ids = partner_obj.s_history_loyalty_point_so_ids[loyalty_point_start_index:loyalty_point_end_index]
            history_green_points_ids = partner_obj.history_green_points_ids[loyalty_point_start_index:loyalty_point_end_index]
            result_msg = self._format_hostory_loyalty_point(history_points_ids, history_so_points_ids, history_green_points_ids)
            request.env['ir.logging'].sudo().create({
                'name': 'api-history-loyalty-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(result_msg) if result_msg else None,
                'func': 'api_call_history_loyalty_points_magento',
                'line': '0',
            })
            return result_msg
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-history-loyalty-points-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_call_history_loyalty_points_magento',
                'line': '0',
            })
            if e.args == 'Magento2 - Odoo bridge is not defined!':
                return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)
            return invalid_response(head='invalid_query', message=e.args)
