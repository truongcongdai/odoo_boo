import datetime
import json
from json import dumps
import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import base64
import time
from ..tools.api_wrapper_shopee import validate_integrate_token

_logger = logging.getLogger(__name__)


class SStockPickings(models.Model):
    _inherit = "stock.picking"

    is_do_shopee = fields.Boolean(string='DO Shopee', related='sale_id.s_shopee_is_order')
    s_shopee_package_number = fields.Char(string="Id Package Shopee")
    s_shopee_logistics_status = fields.Selection([('LOGISTICS_NOT_START', 'LOGISTICS_NOT_START'),
                                                  ('LOGISTICS_REQUEST_CREATED', 'LOGISTICS_REQUEST_CREATED'),
                                                  ('LOGISTICS_PICKUP_DONE', 'LOGISTICS_PICKUP_DONE'),
                                                  ('LOGISTICS_PICKUP_RETRY', 'LOGISTICS_PICKUP_RETRY'),
                                                  ('LOGISTICS_PICKUP_FAILED', 'LOGISTICS_PICKUP_FAILED'),
                                                  ('LOGISTICS_DELIVERY_DONE', 'LOGISTICS_DELIVERY_DONE'),
                                                  ('LOGISTICS_DELIVERY_FAILED', 'LOGISTICS_DELIVERY_FAILED'),
                                                  ('LOGISTICS_REQUEST_CANCELED', 'LOGISTICS_REQUEST_CANCELED'),
                                                  ('LOGISTICS_COD_REJECTED', 'LOGISTICS_COD_REJECTED'),
                                                  ('LOGISTICS_READY', 'LOGISTICS_READY'),
                                                  ('LOGISTICS_INVALID', 'LOGISTICS_INVALID'),
                                                  ('LOGISTICS_LOST', 'LOGISTICS_LOST'),
                                                  ('LOGISTICS_PENDING_ARRANGE', 'LOGISTICS_PENDING_ARRANGE')])
    marketplace_shopee_order_status = fields.Selection([("UNPAID", "UNPAID"),
                                                        ("READY_TO_SHIP", "READY_TO_SHIP"),
                                                        ("PROCESSED", "PROCESSED"),
                                                        ("RETRY_SHIP", "RETRY_SHIP"),
                                                        ("SHIPPED", "SHIPPED"),
                                                        ("TO_CONFIRM_RECEIVE", "TO_CONFIRM_RECEIVE"),
                                                        ("IN_CANCEL", "IN_CANCEL"),
                                                        ("CANCELLED", "CANCELLED"),
                                                        ("TO_RETURN", "TO_RETURN"),
                                                        ("COMPLETED", "COMPLETED")],
                                                       string="Tình trạng đơn hàng Shopee",
                                                       related='sale_id.marketplace_shopee_order_status')
    is_ready_to_ship = fields.Boolean(compute="compute_is_ready_to_ship", store=True)
    shopee_shipping_method = fields.Selection([('pickup', 'Lấy hàng'), ('dropoff', 'Tự mang hàng ra bưu cục')],
                                              string='Phương thức nhận hàng Shopee', default="pickup")
    s_shopee_id_order = fields.Char(string="Id đơn hàng Shopee", readonly=True, related='sale_id.s_shopee_id_order')
    has_label = fields.Boolean(string='Đã tạo shipping label', default=False)

    @api.depends('is_do_shopee')
    def _compute_invisible_btn_cancel(self):
        self.is_invisible_btn_cancel = super(SStockPickings, self)._compute_invisible_btn_cancel()
        if self.is_do_shopee and not self.is_invisible_btn_cancel:
            self.is_invisible_btn_cancel = True
        return self.is_invisible_btn_cancel

    # @api.depends('sale_id.s_shopee_id_order')
    # def _compute_s_shopee_id_order(self):
    #     for rec in self:
    #         if rec.sale_id.s_shopee_is_order and rec.sale_id.s_shopee_id_order:
    #             rec.s_shopee_id_order = rec.sale_id.s_shopee_id_order

    @api.depends('sale_id.marketplace_shopee_order_status')
    def compute_is_ready_to_ship(self):
        for r in self:
            if r.sale_id.marketplace_shopee_order_status == "READY_TO_SHIP" and r.sale_id.s_shopee_is_order:
                r.is_ready_to_ship = True
            else:
                r.is_ready_to_ship = False

    def _get_tracking_info(self, order_sn):
        api = "/api/v2/logistics/get_tracking_info"
        param = {
            "order_sn": order_sn
        }
        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=api, param=param)
        req_json = req.json()
        if req.status_code == 200:
            if not req_json.get('error'):
                return req_json['response']
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: get_tracking_info',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': str(req_json.get('message')),
                    'func': '_get_tracking_info',
                    'line': '0',
                })
        else:
            self.env['ir.config_parameter'].sudo().set_param(
                'advanced_integrate_shopee.is_error_token_shopee', 'True')
            self.env['ir.logging'].sudo().create({
                'name': '#Shopee: get_tracking_info',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(req_json.get('message')),
                'func': '_get_tracking_info',
                'line': '0',
            })

    def btn_push_delivery_method_shopee(self, context=None):
        if context is None: context = {}
        context['package_number'] = self.s_shopee_package_number
        context['order_sn'] = self.sale_id.s_shopee_id_order if self.sale_id.s_shopee_id_order else False
        context['order_name'] = self.sale_id.name if self.sale_id else False
        context['picking_id'] = self.id
        view_id = self.env.ref('advanced_integrate_shopee.s_shopee_display_view_delivery_method_form').id
        return {
            'name': 'Phương thức nhận hàng Shopee',
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 's.shopee.delivery.method',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': '[]',
            'context': context
        }

    def button_validate(self):
        res = super(SStockPickings, self).button_validate()
        if self.sale_id.s_shopee_is_order:
            if self.shopee_shipping_method is False:
                self.shopee_shipping_method = "pickup"
            if self.sale_id.marketplace_shopee_order_status == "UNPAID":
                raise ValidationError('Đơn hàng đang ở trạng thái UNPAID.Không thể Confirm DO')
            elif self.sale_id.marketplace_shopee_order_status == "READY_TO_SHIP" and res == True and self.shopee_shipping_method is not False:
                if self.s_shopee_package_number:
                    # Call api lấy Address_id và Pickup_time_id
                    address_id, pickup_time_id = 0, 0
                    order_sn = self.sale_id.s_shopee_id_order
                    api = "/api/v2/logistics/get_shipping_parameter"
                    param = {
                        "order_sn": order_sn
                    }
                    req_get_shipping = self.env['s.base.integrate.shopee']._get_data_shopee(api=api, param=param)
                    req_get_shipping_json = req_get_shipping.json()
                    if req_get_shipping.status_code == 200:
                        if req_get_shipping_json.get('response'):
                            response_shipping = req_get_shipping_json.get('response')
                            if response_shipping.get('pickup'):
                                pickup_res_shipping = response_shipping.get('pickup')
                                if pickup_res_shipping.get('address_list'):
                                    for address in pickup_res_shipping.get('address_list'):
                                        if 'default_address' in address.get('address_flag'):
                                            # Lấy Address_id mặc định
                                            address_id = address.get('address_id')
                                            # Mặc định lấy pickup_time_id(Ngày J&T lấy hàng) đầu tiên(Trong ngày hôm nay)
                                            if address.get('time_slot_list') and len(address.get('time_slot_list')) > 0:
                                                pickup_time_id = address.get('time_slot_list')[0].get('pickup_time_id')
                                            else:
                                                datetime_now = datetime.datetime.now()
                                                unix_timestamp = int(time.mktime(datetime_now.timetuple()))
                                                pickup_time_id = unix_timestamp
                    else:
                        self.env['ir.config_parameter'].sudo().set_param(
                            'advanced_integrate_shopee.is_error_token_shopee', 'True')
                        self.env['ir.logging'].sudo().create({
                            'name': '#Shopee: api_get_shipping_parameter',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'INFO',
                            'path': 'url',
                            'message': req_get_shipping_json.get('message'),
                            'func': 'api_call_delivery_method_shopee',
                            'line': '0',
                        })
                        raise ValidationError(req_get_shipping_json.get('message'))

                    # Call api phương thức vận chuyển(pick_up or droff_of)
                    url_api_push_delivery_method_shopee = '/api/v2/logistics/ship_order'
                    data_delivery_method = {
                        'order_sn': order_sn
                    }
                    if self.shopee_shipping_method == 'pickup':
                        if order_sn != 0 and address_id != 0 and pickup_time_id != 0:
                            data_delivery_method.update({
                                "pickup": {
                                    'address_id': address_id,
                                    'pickup_time_id': str(pickup_time_id)
                                }
                            })
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': '#Shopee: api-call-delivery-method-shopee',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'INFO',
                                'path': 'url',
                                'message': "Order_sn: %s \t Address_id: %s \t Pickup_time_id: %s" % (
                                    order_sn, address_id, pickup_time_id),
                                'func': 'api_call_delivery_method_shopee',
                                'line': '0',
                            })
                    # elif self.shopee_shipping_method == 'dropoff':
                    #     data_delivery_method.update({
                    #         "dropoff": {}
                    #     })
                    req_push_delivery = self.env['s.base.integrate.shopee']._post_data_shopee(
                        api=url_api_push_delivery_method_shopee,
                        data=json.dumps(data_delivery_method))
                    req_push_delivery_json = req_push_delivery.json()
                    if req_push_delivery.status_code == 200:
                        if req_push_delivery_json.get('error'):
                            self.env['ir.logging'].sudo().create({
                                'name': '#Shopee: api-call-delivery-method-shopee',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'INFO',
                                'path': 'url',
                                'message': str(req_push_delivery_json),
                                'func': 'api_call_delivery_method_shopee',
                                'line': '0',
                            })
                            raise ValidationError(req_push_delivery_json.get('message'))
                        else:
                            return res
                    else:
                        self.env['ir.config_parameter'].sudo().set_param(
                            'advanced_integrate_shopee.is_error_token_shopee', 'True')
                        self.env['ir.logging'].sudo().create({
                            'name': '#Shopee: api-call-delivery-method-shopee',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'INFO',
                            'path': 'url',
                            'message': req_push_delivery_json.get('message'),
                            'func': 'api_call_delivery_method_shopee',
                            'line': '0',
                        })
                        raise ValidationError(req_push_delivery_json.get('message'))
            else:
                return res
        else:
            return res

    def validate_do_shopee(self):
        # Call api lấy Address_id và Pickup_time_id
        address_id, pickup_time_id = 0, 0
        order_sn = self.sale_id.s_shopee_id_order
        api = "/api/v2/logistics/get_shipping_parameter"
        param = {
            "order_sn": order_sn
        }
        req_parameter = self.env['s.base.integrate.shopee']._get_data_shopee(api=api, param=param)
        if req_parameter is not None:
            if req_parameter.get('response') and req_parameter.get('response').get('pickup') and req_parameter.get(
                    'response').get('pickup').get('address_list'):
                for address in req_parameter.get('response').get('pickup').get('address_list'):
                    if 'default_address' in address.get('address_flag'):
                        # Lấy Address_id mặc định
                        address_id = address.get('address_id')
                        # Mặc định lấy pickup_time_id(Ngày J&T lấy hàng) đầu tiên(Trong ngày hôm nay)
                        if address.get('time_slot_list') and len(address.get('time_slot_list')) > 0:
                            pickup_time_id = address.get('time_slot_list')[0].get('pickup_time_id')
                        else:
                            datetime_now = datetime.datetime.now()
                            unix_timestamp = int(time.mktime(datetime_now.timetuple()))
                            pickup_time_id = unix_timestamp
        else:
            self.env['ir.config_parameter'].sudo().set_param(
                'advanced_integrate_shopee.is_error_token_shopee', 'True')
            self.env['ir.logging'].sudo().create({
                'name': '#Shopee: api-call-delivery-method-shopee',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': "Token hết hạn",
                'func': 'api_call_delivery_method_shopee',
                'line': '0',
            })

        # Call api phương thức vận chuyển(pick_up or droff_of)
        url_api_push_delivery_method_shopee = '/api/v2/logistics/ship_order'
        data_delivery_method = {
            'order_sn': order_sn
        }
        if self.shopee_shipping_method == 'pickup':
            if order_sn != 0 and address_id != 0 and pickup_time_id != 0:
                data_delivery_method.update({
                    "pickup": {
                        'address_id': address_id,
                        'pickup_time_id': str(pickup_time_id)
                    }
                })
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: api-call-delivery-method-shopee',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': "Order_sn: %s \t Address_id: %s \t Pickup_time_id: %s" % (
                        order_sn, address_id, pickup_time_id),
                    'func': 'api_call_delivery_method_shopee',
                    'line': '0',
                })
        # elif self.shopee_shipping_method == 'dropoff':
        #     data_delivery_method.update({
        #         "dropoff": {}
        #     })
        req = self.env['s.base.integrate.shopee']._post_data_shopee(
            api=url_api_push_delivery_method_shopee,
            data=json.dumps(data_delivery_method))
        return req, data_delivery_method

    def btn_view_action_print_shipping_label_shopee(self):
        start = time.time()
        picking_shopee_ids = dict()
        picking_shopee_ids['order_list'] = []
        error_shipping_document = []
        ship_document_ids = dict()
        ship_document_ids['order_list'] = []
        can_dowload_label = dict()
        can_dowload_label['order_list'] = []
        for rec in self:
            if rec.sale_id and rec.sale_id.s_shopee_id_order:
                order_sn_status = {
                    "order_sn": rec.sale_id.s_shopee_id_order,
                }
                picking_shopee_ids['order_list'].append(order_sn_status)
        ###Create shipping document
        if len(picking_shopee_ids.get('order_list')) > 0:
            for order_sn in picking_shopee_ids.get('order_list'):
                track_url = "/api/v2/logistics/get_tracking_number"
                track_data = {
                    'order_sn': order_sn.get('order_sn')
                }
                track_number = self.env['s.base.integrate.shopee']._get_data_shopee(api=track_url, param=track_data)
                if track_number.status_code == 200:
                    track_number = track_number.json()
                    if track_number.get('response') != None:
                        if track_number.get('response')['tracking_number']:
                            document_param = {
                                "order_sn": order_sn.get('order_sn'),
                                "tracking_number": track_number.get('response')['tracking_number'],
                                "shipping_document_type": "THERMAL_AIR_WAYBILL"
                            }
                            ship_document_ids['order_list'].append(document_param)
            if len(ship_document_ids.get('order_list')) > 0:
                create_url_api = "/api/v2/logistics/create_shipping_document"
                create_shipping_document = self.env['s.base.integrate.shopee']._post_data_shopee(api=create_url_api,
                                                                                                 data=json.dumps(
                                                                                                     ship_document_ids))
                if create_shipping_document.status_code == 200:
                    create_shipping_document = create_shipping_document.json()
                    if create_shipping_document.get('response') != None:
                        if create_shipping_document.get('response').get('result_list'):
                            for result in create_shipping_document.get('response').get('result_list'):
                                if result.get('fail_error'):
                                    if result.get('order_sn'):
                                        fail_picking = self.filtered(
                                            lambda l: l.sale_id.s_shopee_id_order == result.get('order_sn'))
                                        if fail_picking:
                                            for e in fail_picking:
                                                error_shipping_document.append(
                                                    (0, 0, {'name': e.name, 'message': result.get('fail_error')}))
                                else:
                                    order_sn = {
                                        "order_sn": result.get('order_sn'),
                                    }
                                    can_dowload_label['order_list'].append(order_sn)
            if len(error_shipping_document) > 0:
                attachment = {
                    'binary_data': False,
                    'file_name': 'Shipping Label Shopee Error',
                }
                attachment.update({
                    'failed_print_label': error_shipping_document
                })
                print_attachment = self.env['shipping.label.report.shopee'].create(attachment)
                view_form_id = self.env.ref('advanced_integrate_shopee.s_action_print_shipping_label')
                return {
                    'name': _('Shipping Label Error'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'shipping.label.report.shopee',
                    'views': [(view_form_id.id, 'form')],
                    'target': 'new',
                    'res_id': print_attachment.id
                }
            else:
                download_url_api = "/api/v2/logistics/download_shipping_document"
                picking_shopee_ids.update({
                    "shipping_document_type": "THERMAL_AIR_WAYBILL",
                })
                download_shipping_document = self.env['s.base.integrate.shopee']._post_data_shipping_label_shopee(
                    api=download_url_api,
                    data=json.dumps(picking_shopee_ids))
                if download_shipping_document.status_code == 200:
                    download_shipping_document = download_shipping_document.json()
                    if '%PDF' in str(download_shipping_document.content):
                        data_binary_shipping = base64.b64encode(download_shipping_document.content)
                        attachment = {
                            'binary_data': data_binary_shipping,
                            'file_name': 'Shipping Label Shopee',
                        }
                        print_attachment = self.env['shipping.label.report.shopee'].create(attachment)
                        if print_attachment:
                            view_form_id = self.env.ref('advanced_integrate_shopee.s_action_print_shipping_label')
                            check = time.time() - start
                            print(check)
                            return {
                                'name': _('Shipping Label'),
                                'type': 'ir.actions.act_window',
                                'res_model': 'shipping.label.report.shopee',
                                'views': [(view_form_id.id, 'form')],
                                'target': 'new',
                                'res_id': print_attachment.id
                            }
                    else:
                        if 'error' in str(download_shipping_document.content):
                            error_shipping_document.append(
                                (0, 0, {'name': 'error', 'message': download_shipping_document.text}))
                            attachment = {
                                'binary_data': False,
                                'file_name': 'Shipping Label Shopee',
                            }
                            if len(error_shipping_document):
                                attachment.update({
                                    'failed_print_label': error_shipping_document
                                })
                            print_attachment = self.env['shipping.label.report.shopee'].create(attachment)
                            if print_attachment:
                                view_form_id = self.env.ref('advanced_integrate_shopee.s_action_print_shipping_label')
                                return {
                                    'name': _('Shipping Label'),
                                    'type': 'ir.actions.act_window',
                                    'res_model': 'shipping.label.report.shopee',
                                    'views': [(view_form_id.id, 'form')],
                                    'target': 'new',
                                    'res_id': print_attachment.id
                                }

    def mass_action_reserved_quantity(self):
        for rec in self:
            if rec.state in ['assigned']:
                stock_move = rec.move_ids_without_package
                for r in stock_move:
                    forecast_availability = r.forecast_availability
                    stock_quant = r.product_id.stock_quant_ids.filtered(lambda
                                                                            r: r.location_id.warehouse_id and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id)
                    reserved_quantity = stock_quant.reserved_quantity
                    available_quantity = stock_quant.available_quantity
                    quantity = stock_quant.quantity + reserved_quantity
                    if available_quantity > 0 and available_quantity >= forecast_availability:
                        if forecast_availability != 0:
                            if forecast_availability > reserved_quantity:
                                self._cr.execute(
                                    'update stock_quant set reserved_quantity = %s, quantity = %s where id = %s' % (
                                        str(forecast_availability), str(quantity), str(stock_quant.id)))
                        else:
                            raise ValidationError("Tồn giữ trước đang bằng 0. Vui lòng kiểm tra khả dụng!")
                    else:
                        raise ValidationError("Tồn có thể bán không đủ. Vui lòng kiểm tra lại!")
            else:
                raise ValidationError("DO không ở trạng thái sẵn sàng!")
