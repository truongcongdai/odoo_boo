from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)
import json
import time
from datetime import datetime, timedelta
from odoo.http import request, _logger
import pytz


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'
    to_bravo = fields.Boolean("Đã đẩy lên Bravo", default=False)
    mapping_bravo_ids = fields.Many2many(
        comodel_name='bravo.stock.picking.mappings',
        string='Bravo Mappings',
    )
    synced_cancel_order_to_bravo = fields.Boolean("Đơn cancel không đồng bộ sang Bravo", default=False)

    def format_lines_details(self, pos_order, count_order_line, command):
        res = []
        if pos_order.get('id'):
            order_lines = self.env['pos.order.line'].sudo().search(
                [('order_id', '=', pos_order.get('id')), ('order_id', '=', pos_order.get('id')),
                 ('program_id', '=', False), ('coupon_id', '=', False),
                 ('gift_card_id', '=', False), ('is_line_gift_card', '=', False)])
            start_time = time.time()
            for line in order_lines:
                if line.order_id.synced_cancel_order_to_bravo == True:
                    break
                if (len(
                        line.order_id.picking_ids.location_id.warehouse_id) > 0 and line.order_id.picking_ids.location_id.warehouse_id.is_test_location == False) or \
                        (len(
                            line.order_id.picking_ids.location_dest_id.warehouse_id) > 0 and line.order_id.picking_ids.location_dest_id.warehouse_id.is_test_location == False):
                    if line.qty != 0 and line.product_id.detailed_type == 'product':
                        s_lst_price = line.s_lst_price
                        if line.price_unit == 0:
                            s_lst_price = 0
                        if 0 < line.s_lst_price < line.price_unit:
                            s_lst_price = line.price_unit
                        vals = {
                            'id': line.id,
                            'quantity': line.qty,
                            'price_unit': 0,
                        }
                        if line.product_id and line.product_id.detailed_type == 'product':
                            vals.update({
                                'product_name': line.product_id.ma_vat_tu if line.product_id.ma_vat_tu else '',
                                "product_size": line.product_id.get_product_size() if line.product_id.get_product_size() else "00",
                                'product_barcode': line.product_id.default_code if line.product_id.default_code else '',
                                'product_standard_price': round(int(s_lst_price)) if s_lst_price else 0,

                            })
                        if vals['quantity'] != 0 and vals['product_standard_price'] != 0:
                            vals.update({
                                'price_unit': round(int(round(int(vals['product_standard_price'])) * vals['quantity']))
                            })
                        price_subtotal = round(
                            int(vals.get('price_unit') - line.boo_total_discount_percentage - line.boo_total_discount))
                        discount = vals.get('price_unit') - price_subtotal
                        if line.order_id.is_cancel_order != True:
                            if len(line.refunded_orderline_id) < 1 and len(line.sale_order_line_id) < 1:
                                if vals['price_unit'] < discount:
                                    discount = vals['price_unit']
                                    price_subtotal = vals['price_unit'] - discount
                            else:
                                if vals['price_unit'] > discount:
                                    discount = vals['price_unit']
                                    price_subtotal = vals['price_unit'] - discount
                        vals.update({
                            'discount': discount,
                            'price_subtotal': price_subtotal
                        })
                        if line.order_id:
                            if line.order_id.refunded_orders_count > 0 or line.order_id.sale_order_count > 0:
                                # Đơn hàng hoàn có stock_picking > 1
                                if len(line.order_id.picking_ids) > 1:
                                    for picking in line.order_id.picking_ids:
                                        if picking.location_id and picking.location_id.usage in ('customer', 'transit'):
                                            vals.update({
                                                'location_id': picking.location_dest_id.s_code if
                                                picking.location_dest_id.s_code else '',
                                            })
                                # Đơn hàng hoàn stock_picking = 1
                                elif len(line.order_id.picking_ids) == 1:
                                    if line.order_id.picking_ids and line.order_id.picking_ids.location_id.usage in ('customer', 'transit'):
                                        vals.update({
                                            'location_id': line.order_id.picking_ids.location_dest_id.s_code if
                                            line.order_id.picking_ids.location_dest_id.s_code else '',
                                        })
                                    else:
                                        vals.update({
                                            'location_id': line.order_id.picking_ids.location_id.s_code if
                                            line.order_id.picking_ids.location_id.s_code else '',
                                        })
                            else:
                                for picking in line.order_id.picking_ids:
                                    if picking.location_id and picking.location_id.usage != 'customer':
                                        vals.update({
                                            'location_id': picking.location_id.s_code if
                                            picking.location_id.s_code else '',
                                        })
                        res.append(vals)
            # print('format_lines_details: %s, count: %s' % (time.time() - start_time, len(order_lines),))
            return res, count_order_line + len(order_lines)

    @api.model
    def push_order_to_bravo(self, command, set_date, pos_resync_id):
        try:
            result = {
                "partner": "ODOO",
                "command": command,
            }
            list_mappings_sync_manual = []
            limit = int(self.env['ir.config_parameter'].sudo().get_param('bravo.push.limit', '500'))
            start_time = time.time()
            count = 0
            if pos_resync_id:
                count += 9
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                # CreateRetail
                command_type = False
                # Return order
                query_order_ids = self._cr.execute(
                    """SELECT order_id FROM pos_order_line WHERE refunded_orderline_id IS NOT NULL OR sale_order_line_id IS NOT NULL;""", )
                order_ids = [item[0] for item in self._cr.fetchall()]
                if command == 'CreateReturnRetail':
                    query_pos_order = self._cr.execute(
                        """SELECT id,date_order,pos_reference,is_cancel_order FROM pos_order 
                        WHERE state IN ('paid', 'done', 'invoiced')
                                      AND date_order is not null
                                      AND (id in %s or id in (107792, 105753))
                                      AND (synced_cancel_order_to_bravo is False or synced_cancel_order_to_bravo is null)
                                      AND id NOT IN (SELECT pos_order_id FROM bravo_stock_picking_mappings WHERE pos_order_id is not null AND (status_code='00' OR need_resync_manual IS TRUE) AND post_api in %s) LIMIT %s""",
                        (tuple(order_ids), ('CreateReturnRetail', 'CreateRetail'), limit,))
                    pos_order_ids = self._cr.dictfetchall()
                else:
                    query_pos_order = self._cr.execute(
                        """SELECT id,date_order,pos_reference,is_cancel_order FROM pos_order 
                        WHERE state IN ('paid', 'done', 'invoiced')
                                      AND date_order is not null
                                      AND id not in %s
                                      AND (synced_cancel_order_to_bravo is False or synced_cancel_order_to_bravo is null)
                                      AND id NOT IN (SELECT pos_order_id FROM bravo_stock_picking_mappings WHERE pos_order_id is not null AND (status_code='00' OR need_resync_manual IS TRUE) AND post_api = %s) LIMIT %s""",
                        (tuple(order_ids), command, limit,))
                    pos_order_ids = self._cr.dictfetchall()
                if pos_resync_id and pos_resync_id not in [res['id'] for res in pos_order_ids]:
                    query_pos_order = self._cr.execute(
                        """SELECT id,date_order,pos_reference,is_cancel_order FROM pos_order 
                        WHERE state IN ('paid', 'done', 'invoiced')
                                      AND date_order is not null
                                      AND id = %s""", (pos_resync_id,))
                    list_resync = self._cr.dictfetchall()
                    if list_resync:
                        pos_order_ids = list_resync
                if pos_order_ids:
                    data = []
                    data_unsync = []
                    data_sync = []
                    special_order = []
                    count_order_line = 0
                    start_time_line = time.time()
                    date_done = False
                    for pos in pos_order_ids:
                        if pos.get('is_cancel_order'):
                        ##Có đơn gốc bên Bravo nhưng không có đơn refund => sync
                        ##Không có đơn gốc bên Bravo mà đã hủy order / Không có refund bên Bravo mà đã hủy order => skip
                            order = self.env['pos.order'].sudo().search([('id', '=', pos.get('id'))])
                            stock_picking = order.picking_ids[0]
                            if len(stock_picking) > 0:
                                date_done = order.picking_ids[0].date_done
                            refunded_id = order.refunded_order_ids.id
                            if refunded_id:
                                query_origin_order = self._cr.execute(
                                    """SELECT id FROM pos_order
                                    WHERE id = %s
                                     AND id IN (SELECT pos_order_id FROM bravo_stock_picking_mappings 
                                     WHERE pos_order_id is not null AND status_code='00' AND post_api in %s )""",
                                    (refunded_id, ('CreateReturnRetail', 'CreateRetail'),))
                                origin_order = [item[0] for item in self._cr.fetchall()]
                                if len(origin_order) == 0:
                                    self._cr.execute("""UPDATE pos_order SET synced_cancel_order_to_bravo = TRUE WHERE id = %s""", (refunded_id,))
                                    self._cr.execute("""UPDATE pos_order SET synced_cancel_order_to_bravo = TRUE WHERE id = %s""", (pos.get('id'),))
                            else:
                                self._cr.execute("""UPDATE pos_order SET synced_cancel_order_to_bravo = TRUE WHERE id = %s""", (pos.get('id'),))
                            if order.refund_orders_count > 0 and order.refunded_orders_count > 0:
                                self._cr.execute("""UPDATE pos_order SET synced_cancel_order_to_bravo = TRUE WHERE id = %s""", (pos.get('id'),))

                        details, count_order_line = self.format_lines_details(pos, count_order_line, command)
                        if details:
                            user_tz = self.env.user.tz or pytz.utc
                            tz = pytz.utc.localize(pos.get('date_order')).astimezone(pytz.timezone(user_tz))
                            str_tz = datetime.strftime(tz, "%Y-%m-%d")
                            if date_done != False:
                                date_done_str = datetime.strftime(pytz.utc.localize(date_done).astimezone(pytz.timezone(user_tz)), "%Y-%m-%d")
                                date_done_tz = datetime.strptime(date_done_str, "%Y-%m-%d")
                                ###Đơn hàng hủy -> nhiều ngày sau với hoàn thành -> date_order = date_done
                                if datetime.strptime(str_tz, "%Y-%m-%d") != date_done_tz and datetime.strptime(str_tz, "%Y-%m-%d") < date_done_tz:
                                    str_tz = datetime.strftime(date_done_tz, "%Y-%m-%d")
                            if set_date and datetime.strptime(str_tz, "%Y-%m-%d") <= datetime.strptime(set_date,"%Y-%m-%d"):
                                str_tz = set_date
                            pos_data = {
                                "parent_id": pos.get('id'),
                                "invoice_date": str_tz if str_tz else 'None',
                                "invoice_name": pos.get('pos_reference') if pos.get('pos_reference') else '',
                                "details": details
                            }
                            if pos_data.get('parent_id') == 40354:
                                special_order.append(pos_data)
                            for rec in pos_data['details']:
                                # if rec['product_name'] == '' or rec['product_barcode'] == '':
                                if rec['product_barcode'] == '':
                                    data_unsync.append(pos_data)
                                    break
                            if pos_data not in data_unsync:
                                data_sync.append(pos_data)
                            # data.append(pos_data)
                    print('format_lines_details: %s, count: %s' % (time.time() - start_time_line, count_order_line,))
                    # result['data'] = data
                    token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                    url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
                    if len(data_unsync) > 0:
                        response_text = [{
                            'error_message': 'Dữ liệu bị trống (rỗng)',
                            'error_code': '11'
                        }]
                        mappings = self.env['bravo.stock.picking.mappings'].sudo().import_mapping_bravo(data_unsync, response_text, command)
                        for mapp in mappings:
                            if mapp.pos_order_id.id not in list_mappings_sync_manual:
                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s""", (mapp.id,))
                                list_mappings_sync_manual.append(mapp.pos_order_id.id)
                        self.env['ir.logging'].sudo().create({
                            'name': command,
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'message': str(response_text) + str(data_unsync),
                            'path': 'url',
                            'func': '_post_data_bravo',
                            'line': '0',
                        })
                        error_bravo_config = self.env.ref(
                            'advanced_integrate_bravo.post_sync_error_bravo_config_parameter')
                        if error_bravo_config and error_bravo_config.value == 'False':
                            error_bravo_config.sudo().value = 'True'
                    if len(data_sync) > 0:
                        # self._check_order_api_create_retail_sync_sai(data_sync)
                        if command == 'CreateReturnRetail' or special_order:
                            sync_data_line_return_retail = []
                            sync_data_line_retail = []
                            for order in data_sync:
                                data_line_return_retail = []
                                data_line_retail = []
                                for detail in order['details']:
                                    if detail['quantity'] < 0:
                                        data_line_return_retail.append(detail)
                                    else:
                                        data_line_retail.append(detail)
                                if len(data_line_retail) > 0:
                                    line_retail = ({
                                        'parent_id': order['parent_id'],
                                        'invoice_date': order['invoice_date'],
                                        'invoice_name': order['invoice_name'],
                                        'details': data_line_retail
                                    })
                                    sync_data_line_retail.append(line_retail)
                                if len(data_line_return_retail) > 0:
                                    line_return_retail = ({
                                        'parent_id': order['parent_id'],
                                        'invoice_date': order['invoice_date'],
                                        'invoice_name': order['invoice_name'],
                                        'details': data_line_return_retail
                                    })
                                    sync_data_line_return_retail.append(line_return_retail)
                            ### CreateRetail
                            if len(sync_data_line_retail) > 0:
                                res_command = 'CreateRetail'
                                result = {
                                    "partner": "ODOO",
                                    "command": res_command,
                                }
                                result['data'] = sync_data_line_retail
                                # self._check_sync_data_line_retail(result)
                                res = self.env['base.integrate.bravo']._post_data_bravo(url=url, token=token, command=res_command, data=json.dumps(result))
                                # if res.status_code == 200:
                                #     response_text = res.json()
                                #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(sync_data_line_retail, response_text, res_command)
                                resp = res.json()
                                if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                    response_text = res.json()
                                    mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                    for mapp in mappings:
                                        if mapp.pos_order_id.id not in list_mappings_sync_manual:
                                            self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                            list_mappings_sync_manual.append(mapp.pos_order_id.id)
                                elif res.status_code == 200:
                                    response_text = res.json()
                                    self.env['bravo.stock.picking.mappings'].import_mapping_bravo(sync_data_line_retail, response_text, res_command)
                            ### CreateReturnRetail
                            if len(sync_data_line_return_retail) > 0:
                                res_command = 'CreateReturnRetail'
                                result = {
                                    "partner": "ODOO",
                                    "command": res_command,
                                }
                                result['data'] = sync_data_line_return_retail
                                res = self.env['base.integrate.bravo']._post_data_bravo(url=url, token=token, command=res_command, data=json.dumps(result))
                                # if res.status_code == 200:
                                #     response_text = res.json()
                                #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(sync_data_line_return_retail, response_text, res_command)
                                resp = res.json()
                                if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                    response_text = res.json()
                                    mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                    for mapp in mappings:
                                        if mapp.pos_order_id.id not in list_mappings_sync_manual:
                                            self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                            list_mappings_sync_manual.append(mapp.pos_order_id.id)
                                elif res.status_code == 200:
                                    response_text = res.json()
                                    self.env['bravo.stock.picking.mappings'].import_mapping_bravo(sync_data_line_return_retail, response_text, res_command)
                        else:
                            result['data'] = data_sync
                            res = self.env['base.integrate.bravo']._post_data_bravo(url=url, token=token,
                                                                                    command=command,
                                                                                    data=json.dumps(result))
                            # if res.status_code == 200:
                            #     response_text = res.json()
                            #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text,
                            #                                                                   command)
                            resp = res.json()
                            if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                response_text = res.json()
                                mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                for mapp in mappings:
                                    if mapp.pos_order_id.id not in list_mappings_sync_manual:
                                        self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                        list_mappings_sync_manual.append(mapp.pos_order_id.id)
                            elif res.status_code == 200:
                                response_text = res.json()
                                self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                print(
                    '_format_online_sale_stock_details: %s, count: %s' % (time.time() - start_time, len(pos_order_ids)))
            if count == 10:
                if command == 'CreateRetail':
                    is_create_retail = self.env['ir.config_parameter'].sudo().search([(
                        'key', '=', 'advanced_integrate_bravo.ir_cron_post_retail_sale_bravo_ir_actions_server'
                    )])
                    if is_create_retail:
                        is_create_retail.sudo().write({
                            'value': 'False'
                        })
                else:
                    is_create_return_etail = self.env['ir.config_parameter'].sudo().search([(
                        'key', '=', 'advanced_integrate_bravo.ir_cron_post_return_retail_sale_bravo_ir_actions_server'
                    )])
                    if is_create_return_etail:
                        is_create_return_etail.sudo().write({
                            'value': 'False'
                        })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'push_order_to_bravo',
                'line': '0',
            })

    def _check_order_api_create_retail_sync_sai(self, data_sync, ):
        logging = []
        for data_s in data_sync:
            pos_order = self.env['pos.order'].sudo().search([('id', '=', data_s['parent_id'])])
            price_subtotal_detail = 0
            for detail in data_s['details']:
                price_subtotal_detail += detail['price_subtotal']
            if price_subtotal_detail != int(pos_order.amount_total):
                data_s.update({
                    'tien_chenh_lech': price_subtotal_detail - int(pos_order.amount_total)
                })
                logging.append(data_s)
        if logging:
            self.env['ir.logging'].sudo().create({
                'name': 'Bravo API CreateRetail order chênh lệch tiền',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'message': str(logging),
                'path': 'url',
                'func': '_post_data_bravo',
                'line': '0',
            })

    def _check_sync_data_line_retail(self, result):
        if result:
            logging = []
            for rec in result.get('data'):
                pos_order = self.env['pos.order'].sudo().search([('id', '=', rec['parent_id'])])
                subtotal_ref = 0
                detail_total = 0
                if pos_order:
                    subtotal = pos_order.amount_total
                    line_refund = pos_order.lines.filtered(lambda r: r.refunded_orderline_id or r.sale_order_line_id)
                    for line in line_refund:
                        subtotal_ref += line.price_subtotal
                    for detail in rec['details']:
                        detail_total += detail['price_subtotal']
                    check_total = int(detail_total) + int(subtotal_ref)
                    if check_total != subtotal:
                        rec.update({
                            'tien_chenh_lech': int(subtotal) - int(check_total)
                        })
                        logging.append(rec)
            if logging:
                self.env['ir.logging'].sudo().create({
                    'name': 'Bravo API CreateReturnRetail order chênh lệch tiền của đơn hàng CreateRetail',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'message': str(logging),
                    'path': 'url',
                    'func': '_post_data_bravo',
                    'line': '0',
                })

    # Cron post Bravo - Bảng kê chi tiết hàng bán lẻ
    @api.model
    def _cron_post_bravo_retail_sale(self, set_date=False, pos_resync_id=False):
        command = "CreateRetail"
        return self.push_order_to_bravo(command=command, set_date=set_date, pos_resync_id=pos_resync_id)

    # Cron post Bravo - Bảng kê chi tiết hàng bán lẻ bị trả lại
    @api.model
    def _cron_post_bravo_return_retail_sale(self, set_date=False, pos_resync_id=False):
        command = "CreateReturnRetail"
        return self.push_order_to_bravo(command=command, set_date=set_date, pos_resync_id=pos_resync_id)

    def cron_force_on_off_bravo_cron(self):
        retail = self.env.ref('advanced_integrate_bravo.ir_cron_post_retail_sale_bravo')
        return_retail = self.env.ref('advanced_integrate_bravo.ir_cron_post_return_retail_sale_bravo')
        sucess_order = self.env.ref('advanced_integrate_bravo.ir_cron_post_online_success_order_bravo')
        return_order = self.env.ref('advanced_integrate_bravo.ir_cron_online_sale_success_was_return_bravo')
        return_fail_order = self.env.ref('advanced_integrate_bravo.ir_cron_online_sale_failed_was_return_bravo')
        internal_out_stock = self.env.ref('advanced_integrate_bravo.ir_cron_post_internal_out_stock')
        internal_in_stock = self.env.ref('advanced_integrate_bravo.ir_cron_post_internal_in_stock')
        transfer_online_stock = self.env.ref('advanced_integrate_bravo.ir_cron_post_transfer_online_stock')
        export_inventory = self.env.ref('advanced_integrate_bravo.ir_cron_post_export_inventory')
        adjustment_stock_details = self.env.ref('advanced_integrate_bravo.ir_cron_post_adjustment_stock_details')
        error_bravo_config = self.env.ref('advanced_integrate_bravo.post_sync_error_bravo_config_parameter')
        sended_email = self.env.ref('advanced_integrate_bravo.send_mail_sync_error_bravo_config_parameter')
        list_id = [retail, return_retail, sucess_order, return_order, return_fail_order, internal_out_stock,
                   internal_in_stock, export_inventory, adjustment_stock_details]
        user_tz = self.env.user.tz or pytz.utc
        time_start = datetime.strptime(
            datetime.strftime(pytz.utc.localize(fields.datetime.today()).astimezone(pytz.timezone(user_tz)),
                              "%Y-%m-%d 00:00:00"), '%Y-%m-%d %H:%M:%S')
        time_stop = datetime.strptime(
            datetime.strftime(pytz.utc.localize(fields.datetime.today()).astimezone(pytz.timezone(user_tz)),
                              "%Y-%m-%d 07:00:00"), '%Y-%m-%d %H:%M:%S')
        time_now = datetime.strptime(
            datetime.strftime(pytz.utc.localize(fields.datetime.today()).astimezone(pytz.timezone(user_tz)),
                              "%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
        for rec in list_id:
            param_system = self.env['ir.config_parameter'].sudo().search([('key', '=', rec.xml_id)])
            if param_system:
                if param_system.value == 'True':
                    # cron cho chạy từ 0h - 7h
                    if time_now >= time_start and time_now <= time_stop and rec.active == False:
                        rec.sudo().active = True
                        if error_bravo_config.value == 'True':
                            error_bravo_config.sudo().value = 'False'
                        if sended_email.value == 'True':
                            sended_email.sudo().value = 'False'
                else:
                    # disable cron sau 7h
                    if time_now >= time_stop:
                        rec.sudo().active = False
                        param_system.sudo().write({
                            'value': 'True'
                        })

    def _cron_send_mail_sync_error_bravo(self):
        error_bravo_config = self.env.ref('advanced_integrate_bravo.post_sync_error_bravo_config_parameter')
        retail = self.env.ref('advanced_integrate_bravo.ir_cron_post_retail_sale_bravo')
        return_retail = self.env.ref('advanced_integrate_bravo.ir_cron_post_return_retail_sale_bravo')
        sucess_order = self.env.ref('advanced_integrate_bravo.ir_cron_post_online_success_order_bravo')
        return_order = self.env.ref('advanced_integrate_bravo.ir_cron_online_sale_success_was_return_bravo')
        return_fail_order = self.env.ref('advanced_integrate_bravo.ir_cron_online_sale_failed_was_return_bravo')
        internal_out_stock = self.env.ref('advanced_integrate_bravo.ir_cron_post_internal_out_stock')
        internal_in_stock = self.env.ref('advanced_integrate_bravo.ir_cron_post_internal_in_stock')
        transfer_online_stock = self.env.ref('advanced_integrate_bravo.ir_cron_post_transfer_online_stock')
        export_inventory = self.env.ref('advanced_integrate_bravo.ir_cron_post_export_inventory')
        adjustment_stock_details = self.env.ref('advanced_integrate_bravo.ir_cron_post_adjustment_stock_details')
        list_id = [retail, return_retail, sucess_order, return_order, return_fail_order, internal_out_stock,
                   internal_in_stock, transfer_online_stock, export_inventory, adjustment_stock_details]
        check_active = list(set([res.active for res in list_id]))
        sended_email = self.env.ref('advanced_integrate_bravo.send_mail_sync_error_bravo_config_parameter')
        if error_bravo_config.value == 'True' and len(check_active) == 1 and check_active[0] == False and sended_email.value == 'False':
            users = self.env.ref('advanced_sale.s_boo_group_send_mail').users
            emails = False
            if users:
                emails = list(set([res.email for res in users]))
            subject = _("Lỗi đồng bộ Bravo")
            body = _("""Có lỗi khi đồng bộ từ Odoo -> Bravo. Vui lòng vào kiểm tra đồng bộ""",)
            if emails:
                email = self.env['ir.mail_server'].build_email(
                    email_from=self.env.user.email,
                    email_to=emails,
                    subject=subject, body=body,
                )
                self.env['ir.mail_server'].send_email(email)
                sended_email.sudo().value = 'True'
