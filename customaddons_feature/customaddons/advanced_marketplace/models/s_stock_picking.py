from odoo import fields, models, _, api
import json
import urllib3
import requests
import pdfkit
import datetime, time
from datetime import timedelta
from odoo.exceptions import ValidationError, _logger
import base64
import urllib3
import requests
import io
import shutil, pathlib
from PyPDF2 import PdfFileReader, PdfFileWriter
from odoo.tools.float_utils import float_compare, float_is_zero

urllib3.disable_warnings()


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_printed_label_tiktok = fields.Boolean(default=False)
    s_location_kdd = fields.Boolean(related='location_id.s_is_transit_location', string="KDD của địa điểm nguồn")
    s_location_dest_kdd = fields.Boolean(related='location_dest_id.s_is_transit_location',
                                         string="KDD của địa điểm đích")
    s_mkp_validate_error_unreserved = fields.Boolean(default=False, compute="_compute_s_mkp_validate_error_unreserved", string="Tăng số lượng giữ trước")
    # s_do_marketplace = fields.Boolean(related='sale_id.is_ecommerce_order', string="Là DO đơn marketplace")
    is_lazada_do = fields.Boolean(string='Mã đơn hàng gốc Lazada', related='sale_id.is_lazada_order', store=True)
    is_shopee_do = fields.Boolean(string='DO Shopee', related='sale_id.s_shopee_is_order', store=True)
    is_tiktok_do = fields.Boolean(string="Id Order Tiktok", readonly=True, related='sale_id.is_tiktok_order', store=True)

    def _compute_s_mkp_validate_error_unreserved(self):
        for rec in self:
            rec.s_mkp_validate_error_unreserved = False
            if rec.move_line_ids:
                for ml in rec.move_line_ids:
                    rounding = ml.product_id.uom_id.rounding
                    quants = self.env['stock.quant'].sudo()._gather(ml.product_id, ml.location_id, lot_id=ml.lot_id, package_id=ml.package_id,
                                          owner_id=ml.owner_id, strict=True)
                    reserved_quants = []
                    if float_compare(-ml.product_qty, 0, precision_rounding=rounding) < 0:
                        # if we want to unreserve
                        available_quantity = sum(quants.mapped('reserved_quantity'))
                        if rec.state == 'assigned' and not rec.sale_id.is_return_order and not rec.sale_id.is_magento_order and rec.transfer_type == 'out':
                            if float_compare(abs(-ml.product_qty), available_quantity, precision_rounding=rounding) > 0:
                                rec.s_mkp_validate_error_unreserved = True

    def btn_increase_reserved_quantity_in_warehouse(self):
        for rec in self:
            if rec.state in ['assigned']:
                stock_move = rec.move_ids_without_package
                for r in stock_move:
                    forecast_availability = r.forecast_availability
                    stock_quant = r.product_id.stock_quant_ids.filtered(lambda
                                                                            r: r.location_id.warehouse_id and r.location_id.barcode and r.location_id.warehouse_id.lot_stock_id.id == rec.location_id.id)
                    if stock_quant:
                        reserved_quantity = stock_quant.reserved_quantity
                        available_quantity = stock_quant.available_quantity
                        quantity = stock_quant.quantity + forecast_availability
                        if forecast_availability != 0:
                            if forecast_availability > reserved_quantity:
                                Update_stock = self._cr.execute(
                                    'update stock_quant set reserved_quantity = %s, quantity = %s where id = %s' % (
                                        str(forecast_availability), str(quantity), str(stock_quant.id)))
                                self.s_mkp_validate_error_unreserved = False
                        else:
                            raise ValidationError("Tồn giữ trước đang bằng 0. Vui lòng kiểm tra khả dụng!")
            else:
                raise ValidationError("DO không ở trạng thái sẵn sàng!")

    def shopee_create_shipping_document(self, document_ids, do_shopee):
        print_error, printed = [], []
        url = "/api/v2/logistics/create_shipping_document"
        param = json.dumps({
            "order_list": document_ids
        })
        res = self.env['s.base.integrate.shopee']._post_data_shopee(api=url, data=param)
        res_json = res.json()
        if res.status_code == 200:
            if res_json.get('response') is not None:
                if res_json.get('response').get('result_list'):
                    for result in res_json.get('response').get('result_list'):
                        if result.get('fail_error'):
                            if result.get('order_sn'):
                                fail_picking = do_shopee.filtered(
                                    lambda l: l.sale_id.s_shopee_id_order == result.get('order_sn'))
                                if fail_picking:
                                    for e in fail_picking:
                                        print_error.append(
                                            (0, 0, {'name': e.name, 'floor_ecommerce': "Shopee",
                                                    'message_error': result.get('fail_error')}))
                        else:
                            order_sn = {
                                "order_sn": result.get('order_sn'),
                            }
                            printed.append(order_sn)
                    return printed, print_error

    def shopee_get_shipping_document_result(self, order_list):
        url = "/api/v2/logistics/get_shipping_document_result"
        param = {
            "order_list": order_list
        }
        res = self.env['s.base.integrate.shopee']._post_data_shopee(api=url, data=json.dumps(param))
        res_json = res.json()
        if res.status_code == 200:
            if res_json.get('response') is not None:
                if res_json.get('response').get('result_list'):
                    return res_json.get('response').get('result_list')

    def shopee_download_shipping_document(self, order_list):
        url = "/api/v2/logistics/download_shipping_document"
        param = {
            "shipping_document_type": "THERMAL_AIR_WAYBILL",
            "order_list": order_list
        }
        res = self.env['s.base.integrate.shopee']._post_data_shipping_label_shopee(api=url, data=json.dumps(param))
        if res.status_code == 200:
            return res

    def lazada_get_shipping_document_result(self, do_lazada):
        print_error, packages = [], []
        for rec_lazada in do_lazada:
            if not rec_lazada.shipping_label:
                raise ValidationError("DO %s không có Shipping Label" % (rec_lazada.name,))
            if rec_lazada.package_lazada_id:
                packages.append({
                    "package_id": rec_lazada.package_lazada_id
                })
            else:
                print_error.append(
                    (0, 0, {'name': rec_lazada.name, 'floor_ecommerce': "Lazada",
                            'message': "DO chưa ở trạng thái READY_TO_SHIP"}))
        url_api = "/order/package/document/get"
        param = {
            "getDocumentReq": {
                "doc_type": "PDF",
                "packages": packages
            }
        }
        req = self.env['base.integrate.lazada']._post_data_lazada(api=url_api, parameters=param)
        if req['code'] == '0':
            if "error_msg" not in req:
                url_lazada = req.get('result').get('data').get('pdf_url')
                return url_lazada, print_error
        else:
            self.env['ir.logging'].sudo().create({
                'name': '#Shipping Label hàng Loạt : lazada_get_shipping_document_result',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': '/order/package/document/get',
                'message': req,
                'func': 'lazada_get_shipping_document_result',
                'line': '0',
            })
            return None, None

    def shopee_get_tracking_number(self, order_list):
        if len(order_list) > 0:
            document_ids = []
            track_url = "/api/v2/logistics/get_tracking_number"
            for order_sn in order_list:
                track_data = {
                    'order_sn': order_sn.get('order_sn')
                }
                res = self.env['s.base.integrate.shopee']._get_data_shopee(api=track_url, param=track_data)
                res_json = res.json()
                if res.status_code == 200:
                    if res_json.get('response') != None:
                        if res_json.get('response')['tracking_number']:
                            document_param = {
                                "order_sn": order_sn.get('order_sn'),
                                "tracking_number": res_json.get('response')['tracking_number'],
                                "shipping_document_type": "THERMAL_AIR_WAYBILL"
                            }
                            document_ids.append(document_param)
            if len(document_ids) > 0:
                return document_ids

    def btn_open_shipping_label(self):
        do_shipping = self.filtered(lambda
                                        r: r.sale_id.is_lazada_order == True or r.sale_id.s_shopee_is_order == True or
                                           r.sale_id.is_tiktok_order == True or r.sale_id.is_magento_order == True)
        do_tiktok = self.filtered(lambda r: r.sale_id._fields.get(
            'is_tiktok_order') and r.sale_id.is_tiktok_order == True and r.transfer_type == "out")
        do_lazada = self.filtered(lambda r: r.sale_id._fields.get(
            'is_lazada_order') and r.sale_id.is_lazada_order == True and r.transfer_type == "out")
        do_shopee = self.filtered(lambda r: r.sale_id._fields.get(
            's_shopee_is_order') and r.sale_id.s_shopee_is_order == True and r.transfer_type == "out")
        magento_do_ids = self.filtered(lambda r: r.sale_id._fields.get(
            'is_magento_order') and r.sale_id.is_magento_order == True and r.transfer_type == "out")
        if len(do_shipping) > 0:
            if len(self) > len(do_shipping):
                do_no_shipping_label = (self - do_shipping).mapped('name')
                raise ValidationError("DO %s không có Shipping Label" % (do_no_shipping_label,))
            if len(do_tiktok) <= 30:
                print_errors = []
                output = PdfFileWriter()
                if len(do_tiktok) > 0:
                    for rec_tiktok in do_tiktok:
                        # if not rec_tiktok.shipping_label:
                        #     raise ValidationError("DO %s không có Shipping Label" % (rec_tiktok.name,))
                        url_api = "/api/logistics/shipping_document"
                        param = {
                            "order_id": rec_tiktok.sale_id.tiktok_order_id,
                            "document_type": 'SL_PL',
                        }
                        req = self.env['base.integrate.tiktok']._get_data_tiktok(url_api=url_api, param=param).json()
                        if req['code'] == 0:
                            url_tiktok = req['data']['doc_url']
                            response_content = requests.get(url_tiktok)
                            reader = PdfFileReader(io.BytesIO(response_content.content), strict=False)
                            output.addPage(reader.getPage(0))
                            rec_tiktok.is_printed_label_tiktok = True
                        else:
                            rec_tiktok.is_printed_label_tiktok = False
                            print_errors.append((0, 0, {'id': rec_tiktok.id, 'floor_ecommerce': "Tiktok",
                                                        'name': rec_tiktok.name, 'message_error': req.get('message')}))

                if len(do_lazada) > 0:
                    url_lazada, print_error = self.lazada_get_shipping_document_result(do_lazada)
                    if url_lazada is not None or print_error is not None:
                        if len(print_error) > 0:
                            print_errors.append(print_error)
                        if url_lazada is not None:
                            response_content = requests.get(url_lazada)
                            reader = PdfFileReader(io.BytesIO(response_content.content), strict=False)
                            output.addPage(reader.getPage(0))

                if len(do_shopee) > 0:
                    order_list = []
                    for rec in do_shopee:
                        # if not rec.shipping_label:
                        #     raise ValidationError("DO %s không có Shipping Label" % (rec.name,))
                        if rec.sale_id.s_shopee_id_order:
                            order_list.append({
                                "order_sn": rec.sale_id.s_shopee_id_order
                            })
                    document_ids = self.shopee_get_tracking_number(order_list)
                    if document_ids is not None:
                        printed, print_error = self.shopee_create_shipping_document(document_ids, do_shopee)
                        if len(print_error) > 0:
                            print_errors.extend(print_error)
                        if len(printed) > 0:
                            download_document = self.shopee_download_shipping_document(printed)
                            reader_shopee = PdfFileReader(io.BytesIO(download_document.content), strict=False)
                            output.addPage(reader_shopee.getPage(0))

                if len(magento_do_ids) > 0:
                    url_magento = self.env.ref('magento2x_odoo_bridge.magento2x_channel').url
                    shipping_label_ids = False
                    for magento_do_id in magento_do_ids:
                        if magento_do_id.shipping_label:
                            if not shipping_label_ids:
                                shipping_label_ids = magento_do_id.shipping_label
                            else:
                                shipping_label_ids += '+' + magento_do_id.shipping_label
                        else:
                            raise ValidationError("DO %s không có Shipping Label" % (magento_do_id.name,))
                    if shipping_label_ids and url_magento:
                        url_shipping_label = url_magento + '/giaohangnhanh/webhook/printlabel/orderid/' + shipping_label_ids
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'}
                        url_redirect_shipping_label = requests.get(url_shipping_label, headers=headers)
                        result_m2_return = json.loads(url_redirect_shipping_label.content)
                        stock_picking_error_ids = []
                        if len(result_m2_return.get('invalid_order')) > 0:
                            for r in result_m2_return.get('invalid_order'):
                                stock_picking_error_id = self.sudo().search([('shipping_label', '=', r)], limit=1)
                                if stock_picking_error_id:
                                    stock_picking_error_ids.append(stock_picking_error_id.name)
                        if len(stock_picking_error_ids) > 0:
                            raise ValidationError("DO %s có Shipping Label lỗi" % (stock_picking_error_ids,))
                        if url_redirect_shipping_label.status_code == 200:
                            magento_shipping_label_b64_pdf = pdfkit.from_url(result_m2_return.get('url'))
                            reader = PdfFileReader(io.BytesIO(magento_shipping_label_b64_pdf), strict=False)
                            if reader.numPages > 0:
                                reader_page = 0
                                while reader_page < reader.numPages:
                                    output.addPage(reader.getPage(reader_page))
                                    reader_page += 1

                file_pdf = io.BytesIO()
                output.write(file_pdf)
                if output.getNumPages() !=0:
                    create_shipping_label = {
                        'binary': base64.b64encode(file_pdf.getvalue()),
                        'file_name': 'Shipping Label'
                    }
                    if len(print_errors) != 0:
                        create_shipping_label.update({
                            "print_label_error": print_errors
                        })
                    attachment = self.env['shipping.label.tiktok'].create(create_shipping_label)
                    view_form_id = self.env.ref('advanced_marketplace.s_shipping_label_tiktok')
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
                    raise ValidationError("DO được chọn không có label")
            else:
                raise ValidationError("Không thể in quá 30 bản ghi Tiktok")
        else:
            raise ValidationError("DO không phải là DO của đơn Marketplace và Magento")
