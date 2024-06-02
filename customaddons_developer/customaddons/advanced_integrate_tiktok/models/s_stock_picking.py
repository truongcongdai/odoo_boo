from odoo import fields, models, _, api
import json
import datetime, time
from datetime import timedelta
from odoo.exceptions import ValidationError, _logger
import base64
import urllib3
import requests
import io
import shutil, pathlib
from PyPDF2 import PdfFileReader, PdfFileWriter
from ..tools.api_wrapper_tiktok import validate_integrate_token

urllib3.disable_warnings()


class StockPicking(models.Model):
    _inherit = "stock.picking"
    package_tiktok_id = fields.Char('Package Tiktok', readonly=True)
    is_tiktok_do_return = fields.Boolean(string='Là DO Tiktok trả lại')
    is_awaiting_shipment = fields.Boolean(compute="compute_is_awaiting_shipment")
    marketplace_tiktok_order_status = fields.Selection([("100", "UNPAID"),
                                                        ("111", "AWAITING_SHIPMENT"),
                                                        ("112", "AWAITING_COLLECTION"),
                                                        ("114", "PARTIALLY_SHIPPING"),
                                                        ("121", "IN_TRANSIT"),
                                                        ("122", "DELIVERED"),
                                                        ("130", "COMPLETED"),
                                                        ("140", "CANCELLED")], string="Tình trạng đơn hàng Tiktok",
                                                       related='sale_id.marketplace_tiktok_order_status')
    is_selected_shipping_method = fields.Boolean(default=False)

    delivery_option = fields.Selection([('1', "STANDARD"),
                                        ('2', "EXPRESS"),
                                        ('3', "ECONOMY"),
                                        ('4', "SEND_BY_SELLER")
                                        ], string="Tùy chọn vận chuyển")
    package_status = fields.Selection([('1', 'TO_FULFILL'),
                                       ('2', 'PROCESSING'),
                                       ('3', 'FULFILLING'),
                                       ('4', 'COMPLETED'),
                                       ('5', 'CANCELLED')
                                       ], string="Trạng thái giao hàng tiktok", readonly=True)
    tiktok_shipping_method = fields.Selection([("1", "Pick Up"), ("2", "Drop off")], string="Loại giao hàng Tiktok",
                                              default="1")
    is_printed_label_tiktok = fields.Boolean(default=False)
    s_tiktok_order_id = fields.Char(string="Id Order Tiktok", readonly=True, related='sale_id.tiktok_order_id')
    s_reverse_tiktok_order_id = fields.Char(string="Id Order Tiktok", readonly=True, related='sale_id.tiktok_reverse_order_id')

    @api.depends('sale_id.is_tiktok_order')
    def _compute_invisible_btn_cancel(self):
        self.is_invisible_btn_cancel = super(StockPicking, self)._compute_invisible_btn_cancel()
        if self.sale_id.is_tiktok_order and not self.is_invisible_btn_cancel:
            self.is_invisible_btn_cancel = True
        return self.is_invisible_btn_cancel

    # @api.depends('sale_id.tiktok_order_id')
    # def _compute_s_tiktok_order_id(self):
    #     for rec in self:
    #         if rec.sale_id.is_tiktok_order and rec.sale_id.tiktok_order_id:
    #             rec.s_tiktok_order_id = rec.sale_id.tiktok_order_id

    # @validate_integrate_token
    def get_packages(self, cursors=None):
        url_api = "/api/fulfillment/search"
        payload = {
            "page_size": 20
        }
        if cursors:
            payload.update({"cursor": cursors})
        req = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload)).json()
        if req['code'] == 0:
            id_packages_list = []
            for r in req['data']['package_list']:
                id_packages_list.append(r['package_id'])
            return req['data'], id_packages_list

    # @validate_integrate_token
    def get_package_detail(self, package_id):
        url_api = "/api/fulfillment/detail"
        param = {"package_id": package_id}
        req = self.env['base.integrate.tiktok']._get_data_tiktok(url_api=url_api, param=param).json()
        if req['code'] == 0:
            return req['data']
        else:
            self.env['ir.logging'].sudo().create({
                'name': 'get_package_detail',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': req['message'],
                'func': 'get_package_detail',
                'line': '0',
            })

    # @validate_integrate_token
    def reverse_order(self, offset, param=None):
        if param is None:
            param = {}
        url_api = "/api/reverse/reverse_order/list"
        payload = {
            "offset": offset,
            "size": 100
        }
        payload.update(param)
        req = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api, data=json.dumps(payload)).json()
        if req['code'] == 0:
            return req

    # def btn_select_shipping_method(self):
    #     view = self.env.ref('advanced_integrate_tiktok.s_shipping_method_form_view')
    #     return {
    #         'name': _('Arrange Shipment'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'shipping.method',
    #         'views': [(view.id, 'form')],
    #         'target': 'new',
    #     }

    def compute_is_awaiting_shipment(self):
        if self.sale_id.marketplace_tiktok_order_status == "111" and self.sale_id.is_tiktok_order:
            self.is_awaiting_shipment = True
        else:
            self.is_awaiting_shipment = False

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.sale_id.is_tiktok_order:
            if self.tiktok_shipping_method is False:
                self.tiktok_shipping_method = "1"
            if self.sale_id.marketplace_tiktok_order_status == "100" and not self.package_status:
                raise ValidationError('Đơn hàng chưa được thanh toán')
            elif self.sale_id.marketplace_tiktok_order_status == "111" and self.tiktok_shipping_method is not False and res == True:
                if self.package_tiktok_id:
                    req = self.validate_do_tiktok()
                    if req.get('code') == 0:
                        return res
                    else:
                        raise ValidationError(req.get('message'))
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'Tiktok_Select_shipping_method',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'INFO',
                        'path': 'url',
                        'message': "DO của SO: %s chưa có package_id của tiktok Packge_tiktok_id: %s " % (
                            self.sale_id.name, self.package_tiktok_id),
                        'func': 'button_validate',
                        'line': '0',
                    })
                    raise ValidationError('Validate DO Không Thành Công, Vui lòng kiểm tra lại package_id!')
            else:
                return res
        else:
            return res

    # @validate_integrate_token
    def validate_do_tiktok(self):
        url_api = "/api/fulfillment/rts"
        payload = {
            "package_id": self.package_tiktok_id,
            "pick_up_type": int(self.tiktok_shipping_method)
        }
        req = self.env['base.integrate.tiktok']._post_data_tiktok(url_api=url_api,
                                                                  data=json.dumps(payload)).json()
        return req

    def _mapping_package_shipping(self, sale_order, pay_load):
        try:
            if pay_load.get('data').get('order_status'):
                if pay_load.get('data').get('order_status') in (
                        "AWAITING_SHIPMENT", "AWAITING_COLLECTION", "IN_TRANSIT", "DELIVERED", "COMPLETED"):
                    orders_detail = self.env['sale.order'].sudo().get_order_details(pay_load['data']['order_id'])
                    ###Thêm phí vận chuyển
                    if orders_detail is not None:
                        # delivery_line = sale_order.order_line.filtered(lambda l: l.is_delivery == True)
                        # if not delivery_line:
                        #     if 'shipping_provider' in orders_detail.get('order_list')[0]:
                        #         shipping_provider = orders_detail.get('order_list')[0].get('shipping_provider')
                        #         if orders_detail.get('order_list')[0].get('payment_info'):
                        #             payment_info = orders_detail.get('order_list')[0].get('payment_info')
                        #             if payment_info.get('shipping_fee'):
                        #                 shipping_price = payment_info.get('shipping_fee')
                        #                 shipping_method = self.env['s.sale.order.error'].sudo()._get_shipping_method_tiktok(
                        #                     shipping_provider, shipping_price)
                        #                 if shipping_method:
                        #                     sale_order.carrier_id = shipping_method['carrier_id']
                        #                     is_delivery_line = sale_order._create_delivery_line(shipping_method['carrier_id'],
                        #                                                                         shipping_price)
                        #                     if is_delivery_line:
                        #                         is_delivery_line.sudo().write({
                        #                             'price_unit': shipping_price
                        #                         })
                        if not sale_order.picking_ids[0].package_tiktok_id:
                            if orders_detail.get('order_list'):
                                self.s_get_package_id_tiktok(orders_detail, sale_order)
        except Exception as e:
            _logger.error(e.args)
            self.env['s.sale.order.error'].sudo().create({
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'tiktok_order_id': pay_load['data']['order_id'],
                'order_status': pay_load['data']['order_status']
            })

    def s_get_package_id_tiktok(self, orders_detail, sale_order):
        if orders_detail.get('order_list'):
            if orders_detail.get('order_list')[0].get('package_list'):
                ###mapping package_status và package_tiktok_id
                package_list = orders_detail.get('order_list')[0].get('package_list')
                for rec in package_list:
                    package = self.get_package_detail(rec.get('package_id'))
                    if len(sale_order.picking_ids) and len(sale_order.picking_ids) == 1 and package is not None:
                        sale_order.picking_ids.sudo().write({
                            "package_status": str(package.get('package_status')),
                            "package_tiktok_id": package.get('package_id'),
                            "delivery_option": str(package.get('delivery_option')),
                        })
                    elif len(sale_order.picking_ids) and len(sale_order.picking_ids) > 1 and package is not None:
                        for picking in sale_order.picking_ids:
                            if picking.is_tiktok_do_return == False:
                                picking.sudo().write({
                                    "package_status": str(package.get('package_status')),
                                    "package_tiktok_id": package.get('package_id'),
                                    "delivery_option": str(package.get('delivery_option')),
                                })

    # @validate_integrate_token
    def btn_shipping_label_tiktok(self):
        start_time = time.time()
        url_api = "/api/logistics/shipping_document"
        param = {
            "order_id": self.sale_id.tiktok_order_id,
            "document_type": 'SL_PL'
        }
        req = self.env['base.integrate.tiktok']._get_data_tiktok(url_api=url_api, param=param).json()
        if req['code'] == 0:
            url = req['data']['doc_url']
            return {
                'name': 'Shipping Document',
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
        else:
            raise ValidationError(req['message'])

    # @validate_integrate_token
    def btn_open_shipping_label_tiktok(self):
        if len(self) <= 30:
            print_error = []
            output = PdfFileWriter()

            for rec in self:
                url_api = "/api/logistics/shipping_document"
                param = {
                    "order_id": rec.sale_id.tiktok_order_id,
                    "document_type": 'SL_PL'
                }
                req = self.env['base.integrate.tiktok']._get_data_tiktok(url_api=url_api, param=param).json()
                if req['code'] == 0:
                    url = req['data']['doc_url']
                    response_content = requests.get(url)
                    reader = PdfFileReader(io.BytesIO(response_content.content), strict=False)
                    output.addPage(reader.getPage(0))
                    rec.is_printed_label_tiktok = True
                else:
                    rec.is_printed_label_tiktok = False
                    print_error.append((0, 0, {'id': rec.id, 'name': rec.name, 'message_error': req.get('message')}))
            file_pdf = io.BytesIO()
            output.write(file_pdf)
            create_shipping_label = {
                'binary': base64.b64encode(file_pdf.getvalue()),
                'file_name': 'Shipping Label Tiktok'
            }
            if len(print_error) != 0:
                create_shipping_label.update({
                    "print_label_error": print_error
                })
            attachment = self.env['shipping.label.tiktok'].create(create_shipping_label)
            view_form_id = self.env.ref('advanced_integrate_tiktok.s_shipping_label_tiktok')
            return {
                'name': _('Shipping Label'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'shipping.label.tiktok',
                'views': [(view_form_id.id, 'form')],
                'target': 'new',
                'res_id': attachment.id
            }
        else:
            return ValidationError("Không thể in quá 30 bản ghi")
