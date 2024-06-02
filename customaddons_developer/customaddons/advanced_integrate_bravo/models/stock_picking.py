from datetime import datetime, timedelta
import json
import time
from odoo import fields, models, http, api
from odoo.exceptions import ValidationError
from odoo.http import request, _logger
import pytz


class StockMove(models.Model):
    _inherit = 'stock.picking'

    to_bravo = fields.Boolean(string="Đã đẩy sang Bravo")
    bravo_name = fields.Char(string="Bravo name")
    is_inventory_receiving = fields.Boolean(string="Là phiều nhập thành phẩm",
                                            compute="_compute_is_inventory_receiving",
                                            store=True)
    mapping_bravo_ids = fields.Many2many(
        comodel_name='bravo.stock.picking.mappings',
        string='Bravo Mappings',
    )
    returned_picking_id = fields.Many2one(
        'stock.picking', 'Đơn hàng gốc',
        copy=False, readonly=True)

    @api.depends('location_dest_id')
    def _compute_is_inventory_receiving(self):
        for rec in self:
            rec.sudo().is_inventory_receiving = False
            returned_picking_id = rec.returned_picking_id
            if rec.location_id.usage in ('supplier', 'customer'):
                if returned_picking_id:
                    if returned_picking_id:
                        if returned_picking_id.is_inventory_receiving == False:
                            rec.sudo().is_inventory_receiving = False
                        else:
                            rec.sudo().is_inventory_receiving = True
                else:
                    if rec.location_dest_id.is_inventory_unsync == True:
                        rec.sudo().is_inventory_receiving = True
                    else:
                        rec.sudo().is_inventory_receiving = False
            else:
                if returned_picking_id:
                    if returned_picking_id.is_inventory_receiving == False:
                        rec.sudo().is_inventory_receiving = False
                    else:
                        rec.sudo().is_inventory_receiving = True
                else:
                    rec.sudo().is_inventory_receiving = False

    # def write(self, vals):
    #     if vals.get('state') == 'done':
    #         sale_order_id = self.sale_id
    #         if sale_order_id:
    #             warehouse_online_id = self.env['stock.warehouse'].sudo().search([('is_location_online', '=', True)], limit=1).lot_stock_id.s_transit_location_id.id
    #             location_online = self.env['stock.location'].sudo().search(
    #                 [('id', '=', warehouse_online_id), ('s_is_transit_location', '=', True)])
    #             stock_move_ids = self.env['stock.move'].sudo().search([('picking_id', '=', self.id)])
    #             for move in stock_move_ids:
    #                 if move.product_id.detailed_type == 'product' and (
    #                         sale_order_id.is_magento_order == True or sale_order_id.return_order_id.is_magento_order == True):
    #                     transit_obj = self.env['s.transit.stock.quant'].sudo()
    #                     stock_transit = transit_obj.search([
    #                         ('product_id', '=', move.product_id.id),
    #                         ('location_id', '=', location_online.id)
    #                     ], limit=1)
    #                     value = {
    #                         'location_id': location_online.id,
    #                         'product_id': move.product_id.id,
    #                         'available_quantity': 0,
    #                         'quantity': 0,
    #                         'to_sync_bravo': False
    #                     }
    #                     quantity = 0
    #                     if sale_order_id.sale_order_status:
    #                         if stock_transit:
    #                             if vals.get('sale_order_status') in ('dang_xu_ly', 'dang_giao_hang'):
    #                                 quantity = stock_transit.quantity + move.product_uom_qty
    #                             elif vals.get('sale_order_status') in ('hoan_thanh', 'hoan_thanh_1_phan', 'giao_hang_that_bai', 'huy', 'closed'):
    #                                 quantity = stock_transit.quantity - move.product_uom_qty
    #                                 if quantity < 0:
    #                                     quantity = 0
    #                             value.update({
    #                                 'available_quantity': quantity,
    #                                 'quantity': quantity,
    #                             })
    #                             stock_transit.sudo().unlink()
    #                             transit_obj.create(value)
    #                         else:
    #                             if vals.get('sale_order_status') in ('dang_xu_ly', 'dang_giao_hang'):
    #                                 value.update({
    #                                     'available_quantity': move.product_uom_qty,
    #                                     'quantity': move.product_uom_qty
    #                                 })
    #                             transit_obj.create(value)
    #     return super(StockMove, self).write(vals)

    @api.model
    def _cron_post_bravo_outgoing_stock(self, set_date=False, stock_resync_id=False):
        command = "CreateExportInv"
        return self.post_outgoing_stock_details(command=command, set_date=set_date, stock_resync_id=stock_resync_id)

    @api.model
    def _cron_post_bravo_internal_transfer_out_stock(self, set_date=False, picking_resync_id=False):
        command = "CreateTransferExportInv"
        return self.post_internal_stock_details(command=command, set_date=set_date, picking_resync_id=picking_resync_id)

    @api.model
    def _cron_post_bravo_internal_transfer_in_stock(self, set_date=False, picking_resync_id=False):
        command = "CreateTransferImporttInv"
        return self.post_internal_stock_details(command=command, set_date=set_date, picking_resync_id=picking_resync_id)

    def _cron_post_online_success_order(self, set_date=False, sale_resync_id=False):
        command = "CreateSucessOrder"
        return self.push_online_sale_to_bravo(command=command, set_date=set_date, sale_resync_id=sale_resync_id)

    # Bảng kê chi tiết bill online thành công bị trả lại
    def cron_online_sale_success_was_return_bravo(self, set_date=False, sale_resync_id=False):
        command = "CreateReturnOrder"
        return self.push_online_sale_to_bravo(command=command, set_date=set_date, sale_resync_id=sale_resync_id)

    # Bảng kê chi tiết đơn online chưa thành công bị hoàn hàng
    def cron_online_sale_failed_was_return_bravo(self, set_date=False, sale_resync_id=False):
        command = "CreateFailOrder"
        return self.push_online_sale_to_bravo(command=command, set_date=set_date, sale_resync_id=sale_resync_id)

    @api.model
    def _cron_post_bravo_transfer_online_stock(self, set_date=False, picking_resync_id=False):
        command = "CreateTransferOnlInv"
        return self.post_online_sale_stock_details(command=command, set_date=set_date, picking_resync_id=picking_resync_id)

    # Bảng kê chênh lệch kiểm kê
    def _cron_post_bravo_adjustment_stock_details(self, set_date=False):
        command = "CreateDiffInv"
        return self.post_adjustment_stock_details(command=command, set_date=set_date)

    # @staticmethod
    def _format_outgoing_stock_details(self, stock_picks, set_date_to=False):
        res = []
        details = []
        count_outgoing_stock = 0
        for stock_pick in stock_picks:
            if stock_pick.get('id'):
                split_internal_in = {}
                split_internal_out = {}
                stock_move_ids = self.env['stock.move'].search([('picking_id', '=', stock_pick.get('id'))])
                for move in stock_move_ids:
                    if move.picking_id.bravo_name:
                        break
                        # user_time = self.env.user.tz or pytz.utc
                        # ##Time now
                        # time_now = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone(user_time))
                        # str_time_now = datetime.strftime(time_now, "%Y-%m-%d %H:%M:%S")
                        # time_now_str = (datetime.strptime(str_time_now, '%Y-%m-%d %H:%M:%S') - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
                        # datetime_time_now = datetime.strptime(time_now_str, '%Y-%m-%d %H:%M:%S')
                        #
                        # ##Time stock
                        # time_stock = pytz.utc.localize(stock_pick.get('date_done')).astimezone(pytz.timezone(user_time))
                        # str_time_stock = datetime.strftime(time_stock, "%Y-%m-%d %H:%M:%S")
                        # datetime_time_stock = datetime.strptime(str_time_stock, '%Y-%m-%d %H:%M:%S')
                        #
                        # if datetime_time_stock and datetime_time_stock < datetime_time_now:
                        #     break

                    if (len(
                            move.location_id.warehouse_id) > 0 and move.location_id.warehouse_id.is_test_location == False) or \
                            (len(
                                move.location_dest_id.warehouse_id) > 0 and move.location_dest_id.warehouse_id.is_test_location == False):
                        if move.quantity_done > 0 and move.product_id.detailed_type == 'product':
                            location_id = False
                            quantity_done = 0
                            if move.picking_type_id.code == 'internal':
                                # split_internal_in
                                split_internal_in = {
                                    'location_id': move.location_dest_id.s_code if move.location_dest_id.s_code else "",
                                    'quantity_done': -move.quantity_done,
                                }
                                #split_internal_out
                                split_internal_out = {
                                    'location_id': move.location_id.s_code if move.location_id.s_code else "",
                                    'quantity_done': move.quantity_done,
                                }
                                if not split_internal_out.get('location_id'):
                                    parent_location = self.env['stock.location'].sudo().search(
                                        [('s_code', '=', move.location_id.display_name)], limit=1)
                                    if parent_location:
                                        split_internal_out.update({
                                            'location_id': parent_location.s_code
                                        })
                            if move.origin_returned_move_id:
                                return_move_id = move.origin_returned_move_id.picking_id
                                if return_move_id.picking_type_id.code == 'incoming':
                                    location_id = move.location_id.s_code
                                    quantity_done = -move.quantity_done
                                    if move.picking_id.picking_type_id.code == 'incoming' and move.location_id.usage in ('customer', 'supplier'):
                                        location_id = move.location_dest_id.s_code
                                        quantity_done = move.quantity_done
                                elif return_move_id.picking_type_id.code == 'outgoing':
                                    location_id = move.location_dest_id.s_code
                                    quantity_done = move.quantity_done
                            else:
                                if move.picking_id.picking_type_id.code == 'incoming':
                                    location_id = move.location_dest_id.s_code
                                    quantity_done = -move.quantity_done
                                elif move.picking_id.picking_type_id.code == 'outgoing':
                                    location_id = move.location_id.s_code
                                    quantity_done = move.quantity_done

                            if split_internal_in and split_internal_out:
                                vals = {
                                    "id": move.id,
                                    "product_name": move.product_id.ma_vat_tu if move.product_id.ma_vat_tu else "",
                                    "product_size": move.product_id.get_product_size() if move.product_id.get_product_size() else "00",
                                    "product_barcode": move.product_id.default_code if move.product_id.default_code else "",
                                }
                                split_internal_in.update(vals)
                                split_internal_out.update(vals)
                                if split_internal_in:
                                    details.append(split_internal_in)
                                if split_internal_out:
                                    details.append(split_internal_out)
                            else:
                                details.append({
                                    "id": move.id,
                                    "location_id": location_id if location_id else "",
                                    "product_name": move.product_id.ma_vat_tu if move.product_id.ma_vat_tu else "",
                                    "product_size": move.product_id.get_product_size() if move.product_id.get_product_size() else "00",
                                    "product_barcode": move.product_id.default_code if move.product_id.default_code else "",
                                    "quantity_done": quantity_done if quantity_done else 0,
                                })
                count_outgoing_stock += len(stock_move_ids)
            if details:
                user_tz = self.env.user.tz or pytz.utc
                tz = pytz.utc.localize(stock_pick.get('date_done')).astimezone(pytz.timezone(user_tz))
                str_tz = datetime.strftime(tz, "%Y-%m-%d")
                if set_date_to and datetime.strptime(str_tz, "%Y-%m-%d") <= datetime.strptime(set_date_to, "%Y-%m-%d"):
                    str_tz = set_date_to
                head = {
                    "parent_id": stock_pick.get('id'),
                    "date_done": str_tz if str_tz else "",
                    "name": stock_pick.get('name') if stock_pick.get('name') else "",
                    "note": stock_pick.get('note') if stock_pick.get('note') else "CreateExportInv",
                    "details": details,
                }
                details = []
                res.append(head)
        return res, count_outgoing_stock

    def post_outgoing_stock_details(self, command, set_date, stock_resync_id):
        start_time = time.time()
        try:
            limit = int(self.env['ir.config_parameter'].sudo().get_param('bravo.push.limit', '500'))
            count = 0
            list_mappings_sync_manual = []
            if stock_resync_id:
                count += 9
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                query_stock_picking = self._cr.execute(
                    """SELECT id,name,date_done,note, origin FROM stock_picking 
                    WHERE picking_type_id IN (SELECT id FROM stock_picking_type WHERE code in %s)
                                  AND state='done'
                                  AND date_done is not null 
                                  AND (location_id not in (SELECT id FROM stock_location WHERE s_is_inventory_adjustment_location=TRUE) 
                                  AND location_dest_id not in (SELECT id FROM stock_location WHERE s_is_inventory_adjustment_location=TRUE))
                                  AND transfer_out_id is null 
                                  AND transfer_in_id is null 
                                  AND sale_id is null
                                  AND pos_order_id is null
                                  AND is_inventory_receiving is False
                                  AND id NOT IN (SELECT picking_id FROM bravo_stock_picking_mappings WHERE picking_id IS NOT NULL AND post_api = %s AND (status_code='00' OR need_resync_manual IS TRUE))
                                       LIMIT %s""", (('outgoing', 'incoming', 'internal'), 'CreateExportInv', limit,))
                list_stock_picking = self._cr.dictfetchall()
                if stock_resync_id and stock_resync_id not in [res['id'] for res in list_stock_picking]:
                    query_stock_picking = self._cr.execute(
                        """SELECT id,name,date_done,note, origin FROM stock_picking 
                        WHERE picking_type_id IN (SELECT id FROM stock_picking_type WHERE code in %s)
                                      AND state='done'
                                      AND date_done is not null 
                                      AND (location_id not in (SELECT id FROM stock_location WHERE s_is_inventory_adjustment_location=TRUE) 
                                      AND location_dest_id not in (SELECT id FROM stock_location WHERE s_is_inventory_adjustment_location=TRUE))
                                      AND transfer_out_id is null 
                                      AND transfer_in_id is null 
                                      AND sale_id is null
                                      AND pos_order_id is null
                                      AND is_inventory_receiving is False
                                      AND id = %s
                                      """, (('outgoing', 'incoming', 'internal'), stock_resync_id))
                    list_resync = self._cr.dictfetchall()
                    if list_resync:
                        list_stock_picking = list_resync
                    stock_resync_id = False
                if list_stock_picking:
                    data_unsync = []
                    data_sync = []
                    # records = request.env['stock.picking'].search(domain, limit=limit, offset=offset)
                    data, count_outgoing_stock = self._format_outgoing_stock_details(list_stock_picking, set_date)
                    if data:
                        for rec in data:
                            for detail in rec['details']:
                                if (detail['product_barcode'] == '' or detail['quantity_done'] == 0
                                        or detail['location_id'] in ('PARTNER', 'VENDORS') or detail['location_id'] == ''):
                                    data_unsync.append(rec)
                                    break
                            if rec not in data_unsync:
                                data_sync.append(rec)
                    token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                    url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
                    if len(data_unsync) > 0:
                        result = {
                            "partner": "ODOO",
                            "command": command,
                            "data": data_unsync
                        }
                        response_text = [{
                            'error_message': 'Dữ liệu bị trống (rỗng).',
                            'error_code': 11
                        }]
                        mappings = self.env['bravo.stock.picking.mappings'].sudo().import_mapping_bravo(data_unsync, response_text, command)
                        for mapp in mappings:
                            if mapp.picking_id.id not in list_mappings_sync_manual:
                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s""", (mapp.id,))
                                list_mappings_sync_manual.append(mapp.picking_id.id)
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
                        result = {
                            "partner": "ODOO",
                            "command": command,
                            "data": data_sync
                        }
                        result = json.dumps(result)
                        res = self.env['base.integrate.bravo']._post_data_bravo(url, token=token, command=command,
                                                                                data=result)
                        # if res.status_code == 200:
                        #     response_text = res.json()
                        #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text,
                        #                                                                   command)
                        resp = res.json()
                        if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                            response_text = res.json()
                            mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                            for mapp in mappings:
                                if mapp.picking_id.id not in list_mappings_sync_manual:
                                    self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                    list_mappings_sync_manual.append(mapp.picking_id.id)
                        elif res.status_code == 200:
                            response_text = res.json()
                            self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                    print('post_outgoing_stock_details: %s, count_picking: %s, lines:%s' % (
                        time.time() - start_time, len(list_stock_picking), count_outgoing_stock,))
                # offset += len(records)
            if count == 10:
                is_create_export_inventory = self.env['ir.config_parameter'].sudo().search([(
                    'key', '=', 'advanced_integrate_bravo.ir_cron_post_export_inventory_ir_actions_server'
                )])
                if is_create_export_inventory:
                    is_create_export_inventory.sudo().write({
                        'value': 'False'
                    })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'post_outgoing_stock_details',
                'line': '0',
            })

    # Bảng kê chi tiết phiếu xuất kho

    # @staticmethod
    def format_stock_details(self, stock_picks, set_date_to=False):
        res = []
        details = []
        count_stock_pick = 0
        # location_online = self.env.ref('advanced_integrate_bravo.s_location_online_data')
        for stock_pick in stock_picks:
            if stock_pick.get('id'):
                stock_move_ids = self.env['stock.move'].search([('picking_id', '=', stock_pick.get('id'))])
                for move in stock_move_ids:
                    if (len(
                            move.location_id.warehouse_id) > 0 and move.location_id.warehouse_id.is_test_location == False) or \
                            (len(
                                move.location_dest_id.warehouse_id) > 0 and move.location_dest_id.warehouse_id.is_test_location == False):
                        if move.quantity_done > 0 and move.product_id.detailed_type == 'product':
                            if move.product_id.default_code not in ['1112', '1113', '1114', '1115',
                                                                    '003'] and move.product_id.active != False:
                                details.append({
                                    "id": move.id,
                                    "product_name": move.product_id.ma_vat_tu if move.product_id.ma_vat_tu else "",
                                    "product_size": move.product_id.get_product_size() if move.product_id.get_product_size() else "00",
                                    "product_barcode": move.product_id.default_code if move.product_id.default_code else "",
                                    "location_id": move.location_id.s_code if move.location_id else "",
                                    'location_dest_id': move.location_dest_id.s_code if move.location_dest_id else "",
                                    "quantity_done": move.quantity_done if move.quantity_done else 0,
                                })
                count_stock_pick += len(stock_move_ids)
                if details:
                    user_tz = self.env.user.tz or pytz.utc
                    tz = pytz.utc.localize(stock_pick.get('date_done')).astimezone(pytz.timezone(user_tz))
                    str_tz = datetime.strftime(tz, "%Y-%m-%d")
                    if set_date_to and datetime.strptime(str_tz, "%Y-%m-%d") <= datetime.strptime(set_date_to, "%Y-%m-%d"):
                        str_tz = set_date_to
                    head = {
                        "parent_id": stock_pick.get('id'),
                        "date_done": str_tz if str_tz else "",
                        "name": stock_pick.get('name') if stock_pick.get('name') else "",
                        "details": details,
                    }
                    details = []
                    res.append(head)
        return res, count_stock_pick

    def post_internal_stock_details(self, command, set_date, picking_resync_id):
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
            limit = int(self.env['ir.config_parameter'].sudo().get_param('bravo.push.limit', '500'))
            start_time = time.time()
            count = 0
            if picking_resync_id:
                count += 9
            list_mappings_sync_manual = []
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                list_stock_picking = {}
                if command == 'CreateTransferImporttInv':
                    # CreateTransferImporttInv
                    query_stock_picking = self._cr.execute(
                        """SELECT id,name,date_done,sale_id, origin FROM stock_picking 
                        WHERE picking_type_id IN (SELECT id FROM stock_picking_type WHERE code = 'internal')
                        
                                      AND state='done'
                                      AND transfer_out_id is null 
                                      AND transfer_in_id is not null 
                                      AND id NOT IN (SELECT picking_id FROM bravo_stock_picking_mappings WHERE picking_id IS NOT NULL AND post_api = %s AND (status_code='00' OR need_resync_manual IS TRUE))
                                       LIMIT %s""", ('CreateTransferImporttInv', limit,))
                    list_stock_picking = self._cr.dictfetchall()
                elif command == 'CreateTransferExportInv':
                    query_stock_picking = self._cr.execute(
                        """SELECT id,name,date_done,sale_id, origin FROM stock_picking 
                        WHERE picking_type_id IN (SELECT id FROM stock_picking_type WHERE code = 'internal')
                                      AND state='done'
                                      AND transfer_out_id is not null 
                                      AND transfer_in_id is null 
                                      AND id NOT IN (SELECT picking_id FROM bravo_stock_picking_mappings WHERE picking_id is not null AND post_api = %s AND (status_code='00' OR need_resync_manual IS TRUE))
                                       LIMIT %s""", ('CreateTransferExportInv', limit,))
                    list_stock_picking = self._cr.dictfetchall()
                # data, count_stock_picking = self.format_stock_details(list_stock_picking)
                if picking_resync_id and picking_resync_id not in [res['id'] for res in list_stock_picking]:
                    query_stock_picking = self._cr.execute(
                        """SELECT id,name,date_done,sale_id, origin FROM stock_picking 
                        WHERE picking_type_id IN (SELECT id FROM stock_picking_type WHERE code = 'internal')
                                      AND state='done'
                                      AND (transfer_out_id is not null or transfer_in_id is not null )
                                      AND id = %s
                                      """, (picking_resync_id,))
                    list_resync = self._cr.dictfetchall()
                    if list_resync:
                        list_stock_picking = list_resync
                if list_stock_picking:
                    data_unsync = []
                    data_sync = []
                    data, count_stock_picking = self.format_stock_details(list_stock_picking, set_date)
                    if data:
                        for rec in data:
                            for detail in rec['details']:
                                if detail['product_name'] == '' or detail['product_barcode'] == '' or detail[
                                    'quantity_done'] == 0:
                                    data_unsync.append(rec)
                                    break
                            if rec not in data_unsync:
                                data_sync.append(rec)
                    token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                    if len(data_unsync) > 0:
                        result = {
                            "partner": "ODOO",
                            "command": command,
                            "data": data_unsync
                        }
                        response_text = [{
                            'error_message': 'Dữ liệu bị trống (rỗng)',
                            'error_code': 11
                        }]
                        mappings = self.env['bravo.stock.picking.mappings'].sudo().import_mapping_bravo(data_unsync, response_text, command)
                        for mapp in mappings:
                            if mapp.picking_id.id not in list_mappings_sync_manual:
                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s""",(mapp.id,))
                                list_mappings_sync_manual.append(mapp.picking_id.id)
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
                        result = {
                            "partner": "ODOO",
                            "command": command,
                            "data": data_sync
                        }
                        result = json.dumps(result)
                        res = self.env['base.integrate.bravo']._post_data_bravo(url, token, command, data=result)
                        # if res.status_code == 200:
                        #     response_text = res.json()
                        #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text,
                        #                                                                   command)
                        resp = res.json()
                        if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                            response_text = res.json()
                            mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                            for mapp in mappings:
                                if mapp.picking_id.id not in list_mappings_sync_manual:
                                    self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """,(mapp.id,))
                                    list_mappings_sync_manual.append(mapp.picking_id.id)
                        elif res.status_code == 200:
                            response_text = res.json()
                            self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                    print('post_internal_stock_details: time:%s, count: %s, lines: %s',
                          (time.time() - start_time, len(list_stock_picking), count_stock_picking))
                    self.env.cr.commit()
            if count == 10:
                if command == 'CreateTransferImporttInv':
                    is_create_transfer_import_inv = self.env['ir.config_parameter'].sudo().search([(
                        'key', '=', 'advanced_integrate_bravo.ir_cron_post_internal_in_stock_ir_actions_server'
                    )])
                    if is_create_transfer_import_inv:
                        is_create_transfer_import_inv.sudo().write({
                            'value': 'False'
                        })
                else:
                    is_create_transfer_export_inv = self.env['ir.config_parameter'].sudo().search([(
                        'key', '=', 'advanced_integrate_bravo.ir_cron_post_internal_out_stock_ir_actions_server'
                    )])
                    if is_create_transfer_export_inv:
                        is_create_transfer_export_inv.sudo().write({
                            'value': 'False'
                        })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'post_internal_stock_details',
                'line': '0',
            })

    # Bảng kê chi tiết phiếu xuất điều chuyển

    def stock_picking_format_move_lines_details(self, line, command):
        res = []
        sale_order_status = line.get('sale_order_status')
        stock_move_ids = self.env['stock.move'].sudo().search(
            [('picking_id', '=', line.get('id')), ('sale_line_id', '!=', False)])
        warehouse_online_id = self.env['stock.warehouse'].sudo().search([('is_location_online', '=', True)], limit=1).lot_stock_id.s_transit_location_id.id
        location_online = self.env['stock.location'].sudo().search([('id', '=', warehouse_online_id), ('s_is_transit_location', '=', True)])
        if command == "CreateFailOrder":
            for line in stock_move_ids:
                if line.origin_returned_move_id:
                    if (len(
                            line.location_id.warehouse_id) > 0 and line.location_id.warehouse_id.is_test_location == False) or \
                            (len(
                                line.location_dest_id.warehouse_id) > 0 and line.location_dest_id.warehouse_id.is_test_location == False):
                        if line.sale_line_id.product_uom_qty != 0 and line.product_id.detailed_type == 'product':
                            # CreateReturnOrder
                            res.append({
                                'id': line.sale_line_id.id,
                                'product_name': line.product_id.ma_vat_tu if line.product_id.ma_vat_tu else "",
                                "product_size": line.product_id.get_product_size() if line.product_id.get_product_size() else "00",
                                'product_barcode': line.product_id.default_code if line.product_id.default_code else '',
                                'location_id': location_online.s_code if location_online.s_code else "",
                                'old_location_id': line.origin_returned_move_id.location_id.s_code if line.origin_returned_move_id else "",
                                'location_dest_id': line.location_dest_id.s_code if line.location_dest_id.s_code else "",
                                'quantity_done': -line.quantity_done if line.quantity_done else 0,
                            })
        else:
            is_magento_order = False
            if len(stock_move_ids) > 0:
                if stock_move_ids[0].sale_line_id.order_id.is_magento_order:
                    is_magento_order = True
            for line in stock_move_ids:
                if (len(
                        line.location_id.warehouse_id) > 0 and line.location_id.warehouse_id.is_test_location == False) or \
                        (len(
                            line.location_dest_id.warehouse_id) > 0 and line.location_dest_id.warehouse_id.is_test_location == False):
                    if line.sale_line_id.product_uom_qty != 0 and line.product_id.detailed_type == 'product':
                        if line.sale_line_id.order_id:
                            if line.sale_line_id.order_id.pos_order_count > 0:
                                quantity_done = line.sale_line_id.product_uom_qty
                            else:
                                quantity_done = line.sale_line_id.qty_delivered
                        # CreateReturnOrder
                        if command == 'CreateReturnOrder':
                            quantity_done = line.sale_line_id.product_uom_qty
                        location = False
                        location_dest = False
                        if len(line.sale_line_id.refunded_orderline_id):
                            location = location_online.s_code
                            location_dest = line.location_dest_id.s_code
                        else:
                            location = line.location_id.s_code
                            location_dest = location_online.s_code
                        if (
                                sale_order_status == 'hoan_thanh_1_phan' or sale_order_status == 'hoan_thanh') and command == 'CreateSucessOrder':
                            if quantity_done <= 0 and line.move_dest_ids:
                                quantity_done = line.quantity_done
                            # Trường hợp so tạo tay ở odoo
                            if quantity_done <= 0 and line.picking_type_id.code == 'incoming':
                                quantity_done = -line.quantity_done
                                location = location_online.s_code
                                location_dest = line.location_dest_id.s_code
                        vals = {
                            'id': line.sale_line_id.id,
                            'product_name': line.product_id.ma_vat_tu if line.product_id.ma_vat_tu else "",
                            "product_size": line.product_id.get_product_size() if line.product_id.get_product_size() else "00",
                            'product_barcode': line.product_id.default_code if line.product_id.default_code else "",
                            'location_id': location if location else "",
                            'location_dest_id': location_dest if location_dest else "",
                            'quantity_done': quantity_done if quantity_done else 0,
                            'product_cost': round(
                                int(line.product_id.lst_price)) if line.product_id.lst_price else 0,
                            'so_line_price': 0,
                        }
                        if is_magento_order:
                            if quantity_done == line.sale_line_id.product_uom_qty:
                                so_line_discount = round(int(line.sale_line_id.m2_total_line_discount)) + round(
                                    int(line.sale_line_id.boo_total_discount))
                            else:
                                so_line_discount = int((round(int(line.sale_line_id.m2_total_line_discount)) + round(
                                    int(line.sale_line_id.boo_total_discount)) * quantity_done) / line.sale_line_id.product_uom_qty)
                            vals.update({
                                'so_line_discount': so_line_discount,
                                'so_line_price_subtotal': round(
                                    int(line.product_id.lst_price)) * int(quantity_done) - so_line_discount,
                            })
                        else:
                            if 0 < line.sale_line_id.price_unit < line.sale_line_id.product_id.lst_price:
                                total_line_price = round(line.sale_line_id.product_id.lst_price) * int(quantity_done)
                            else:
                                total_line_price = round(line.sale_line_id.price_unit) * int(quantity_done)
                            if quantity_done == line.sale_line_id.product_uom_qty:
                                so_line_discount = round(
                                    int(line.sale_line_id.boo_total_discount_percentage)) + round(
                                    int(line.sale_line_id.boo_total_discount))
                                if command == 'CreateReturnOrder':
                                    if quantity_done < 0:
                                        so_line_discount = round(
                                            int(line.sale_line_id.boo_total_discount_percentage)) - round(
                                            int(line.sale_line_id.boo_total_discount))
                            else:
                                so_line_discount = int(((round(
                                    int(line.sale_line_id.boo_total_discount_percentage)) + round(int(
                                    line.sale_line_id.boo_total_discount))) * quantity_done) / line.sale_line_id.product_uom_qty)
                                if command == 'CreateReturnOrder':
                                    if quantity_done < 0 and line.sale_line_id.product_uom_qty < 0:
                                        so_line_discount = int(((round(
                                            int(line.sale_line_id.boo_total_discount_percentage)) - round(int(
                                            line.sale_line_id.boo_total_discount))) * quantity_done) / line.sale_line_id.product_uom_qty)
                            vals.update({
                                'so_line_discount': so_line_discount,
                                'so_line_price_subtotal': total_line_price - so_line_discount,
                            })
                        if vals['quantity_done'] != 0 and vals['product_cost'] != 0:
                            vals.update({
                                'so_line_price': round(int(vals['quantity_done'] * vals['product_cost']))
                            })
                        if (
                                sale_order_status == 'hoan_thanh_1_phan' or sale_order_status == 'hoan_thanh') and command == 'CreateSucessOrder':
                            if line.origin_returned_move_id:
                                quantity_done = -line.quantity_done
                                location = location_online.s_code
                                location_dest = line.location_dest_id.s_code
                                vals.update({
                                    'location_id': location if location else "",
                                    'old_location_id': line.origin_returned_move_id.location_id.s_code if line.origin_returned_move_id else "",
                                    'location_dest_id': location_dest if location_dest else "",
                                    'quantity_done': quantity_done if quantity_done else 0,
                                })
                            # Trường hợp so tạo tay ở odoo
                            elif quantity_done < 0 and line.picking_type_id.code == 'incoming':
                                vals.update({
                                    'old_location_id': location_dest if location_dest else "",
                                })
                            # if quantity_done == 0 and line.move_dest_ids:
                            #     return res, len(stock_move_ids)
                        res.append(vals)
        return res, len(stock_move_ids)

    def push_online_sale_to_bravo(self, command, set_date, sale_resync_id):
        try:
            limit = int(self.env['ir.config_parameter'].sudo().get_param('bravo.push.limit', '500'))
            result = {
                "partner": "ODOO",
                "command": command,
            }
            list_mappings_sync_manual = []
            start_time = time.time()
            count = 0
            if sale_resync_id:
                count += 9
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                if command == 'CreateSucessOrder':
                    query_sale_ids = self._cr.execute(
                        """SELECT id FROM sale_order WHERE sale_order_status in ('hoan_thanh','hoan_thanh_1_phan') AND state='sale'
                                      AND id not in (SELECT sale_order_id FROM bravo_stock_picking_mappings WHERE sale_order_id is not null AND (status_code='00' OR need_resync_manual IS TRUE) AND post_api in %s)
                                      AND return_order_id is null LIMIT %s""", (('CreateSucessOrder', 'CreateFailOrder'), limit,))
                    sale_ids = [item[0] for item in self._cr.fetchall()]
                elif command == 'CreateReturnOrder':
                    query_sale_ids = self._cr.execute(
                        """SELECT id FROM sale_order WHERE sale_order_status in ('hoan_thanh','hoan_thanh_1_phan') AND state='sale' 
                                     AND return_order_id is not null
                                     AND id not in (SELECT sale_order_id FROM bravo_stock_picking_mappings WHERE sale_order_id is not null AND (status_code='00' OR need_resync_manual IS TRUE) AND post_api in %s ) 
                                     LIMIT %s""", (('CreateSucessOrder', 'CreateReturnOrder'), limit,))
                    sale_ids = [item[0] for item in self._cr.fetchall()]
                # command == 'CreateFailOrder'
                else:
                    query_sale_ids = self._cr.execute(
                        """SELECT id FROM sale_order WHERE sale_order_status not in ('hoan_thanh','hoan_thanh_1_phan') 
                                     
                                     AND id not in (SELECT sale_order_id FROM bravo_stock_picking_mappings WHERE sale_order_id is not null AND (status_code='00' OR need_resync_manual IS TRUE) AND post_api = %s) 
                                     """, (command,))
                    sale_ids = [item[0] for item in self._cr.fetchall()]
                if len(sale_ids) > 0:
                    query_stock_picking = self._cr.execute(
                        """SELECT sp.id,sp.date_done,sp.sale_id,so.is_magento_order, sp.s_origin, so.completed_date, so.sale_order_status FROM stock_picking as sp 
                        INNER JOIN sale_order as so ON sp.sale_id = so.id
                        WHERE sp.sale_id is not null
                                      AND sp.state='done' AND so.completed_date is not null
                                      AND sp.sale_id in %s
                                      """, (tuple(sale_ids),))
                    list_stock_picking = self._cr.dictfetchall()
                    if sale_resync_id and sale_resync_id not in sale_ids:
                        query_stock_picking = self._cr.execute(
                            """SELECT sp.id,sp.date_done,sp.sale_id,so.is_magento_order, sp.s_origin, so.completed_date, so.sale_order_status FROM stock_picking as sp 
                            INNER JOIN sale_order as so ON sp.sale_id = so.id
                            WHERE sp.sale_id is not null
                                          AND sp.state='done' AND so.completed_date is not null
                                          AND sp.sale_id = %s
                                          """, (sale_resync_id,))
                        list_resync = self._cr.dictfetchall()
                        if list_resync:
                            list_stock_picking = list_resync
                        sale_resync_id = False
                    if len(list_stock_picking) > 0:
                        data = []
                        data_unsync = []
                        data_sync = []
                        count_sale_line = 0
                        start_time_so_line = time.time()
                        for picking in list_stock_picking:
                            details, count_so_line = self.stock_picking_format_move_lines_details(picking, command)
                            if details:
                                user_tz = self.env.user.tz or pytz.utc
                                tz = pytz.utc.localize(picking.get('completed_date')).astimezone(pytz.timezone(user_tz))
                                str_tz = datetime.strftime(tz, "%Y-%m-%d")
                                if set_date and datetime.strptime(str_tz, "%Y-%m-%d") <= datetime.strptime(set_date,"%Y-%m-%d"):
                                    str_tz = set_date
                                move_data = {
                                    "parent_id": picking.get('sale_id'),
                                    "invoice_date": str_tz if str_tz else 'None',
                                    "sale_name": picking.get('s_origin'),
                                    "details": details,
                                }
                                ###Check completed_date khi sync qua Bravo
                                date_time_now = datetime.strptime(datetime.strftime(pytz.utc.localize(fields.datetime.today()).astimezone(pytz.timezone(user_tz)),
                              "%Y-%m-%d 00:00:00"), '%Y-%m-%d %H:%M:%S')
                                if (datetime.strptime(move_data['invoice_date'], "%Y-%m-%d")).date() < (date_time_now - timedelta(days=1)).date():
                                    if move_data.get('parent_id') not in [res['parent_id'] for res in data_unsync]:
                                        data_unsync.append(move_data)
                                for rec in move_data['details']:
                                    if rec['product_barcode'] == '' or rec['quantity_done'] == 0:
                                        data_unsync.append(move_data)
                                        break
                                if move_data.get('parent_id') not in [res['parent_id'] for res in data_unsync]:
                                    data_sync.append(move_data)
                                # data.append(move_data)
                                count_sale_line += count_so_line
                        print("stock_picking_format_move_lines_details: %s, count: %s" % (
                            time.time() - start_time_so_line, count_sale_line,))
                        # result['data'] = data
                        token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                        bravo_url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '')
                        if len(data_unsync) > 0:
                            response_text = [{
                                'error_message': 'Dữ liệu bị trống (rỗng) hoặc Dữ liệu Json Data không hợp lệ.',
                                'error_code': 11
                            }]
                            mappings = self.env['bravo.stock.picking.mappings'].sudo().import_mapping_bravo(data_unsync, response_text, command)
                            for mapp in mappings:
                                if mapp.sale_order_id.id not in list_mappings_sync_manual:
                                    self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s""", (mapp.id,))
                                    list_mappings_sync_manual.append(mapp.sale_order_id.id)
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
                            if command == 'CreateReturnOrder':
                                sync_data_line_return_order = []
                                sync_data_line_success_order = []
                                for order in data_sync:
                                    data_line_return_order = []
                                    data_line_success_order = []
                                    for detail in order['details']:
                                        if detail['quantity_done'] < 0:
                                            data_line_return_order.append(detail)
                                        else:
                                            data_line_success_order.append(detail)
                                    if len(data_line_success_order) > 0:
                                        line_success_order = ({
                                            'parent_id': order['parent_id'],
                                            'invoice_date': order['invoice_date'],
                                            'sale_name': order['sale_name'],
                                            'details': data_line_success_order
                                        })
                                        sync_data_line_success_order.append(line_success_order)
                                    if len(data_line_return_order) > 0:
                                        line_return_order = ({
                                            'parent_id': order['parent_id'],
                                            'invoice_date': order['invoice_date'],
                                            'sale_name': order['sale_name'],
                                            'details': data_line_return_order
                                        })
                                        sync_data_line_return_order.append(line_return_order)
                                ### CreateSucessOrder
                                if len(sync_data_line_success_order) > 0:
                                    res_command = 'CreateSucessOrder'
                                    result = {
                                        "partner": "ODOO",
                                        "command": res_command,
                                    }
                                    result['data'] = sync_data_line_success_order
                                    res = self.env['base.integrate.bravo']._post_data_bravo(
                                        url=bravo_url + '/api/bravowebapi/execute', token=token,
                                        command=res_command, data=json.dumps(result))
                                    # if res.status_code == 200:
                                    #     response_text = res.json()
                                    #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(
                                    #         sync_data_line_success_order, response_text, res_command)
                                    resp = res.json()
                                    if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                        response_text = res.json()
                                        mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                        for mapp in mappings:
                                            if mapp.sale_order_id.id not in list_mappings_sync_manual:
                                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                                list_mappings_sync_manual.append(mapp.sale_order_id.id)
                                    elif res.status_code == 200:
                                        response_text = res.json()
                                        self.env['bravo.stock.picking.mappings'].import_mapping_bravo(sync_data_line_success_order, response_text, res_command)
                                ## CreateReturnOrder
                                if len(sync_data_line_return_order) > 0:
                                    res_command = 'CreateReturnOrder'
                                    result = {
                                        "partner": "ODOO",
                                        "command": res_command,
                                    }
                                    result['data'] = sync_data_line_return_order
                                    res = self.env['base.integrate.bravo']._post_data_bravo(
                                        url=bravo_url + '/api/bravowebapi/execute', token=token,
                                        command=res_command, data=json.dumps(result))
                                    # if res.status_code == 200:
                                    #     response_text = res.json()
                                    #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(
                                    #         sync_data_line_return_order, response_text, res_command)
                                    resp = res.json()
                                    if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                        response_text = res.json()
                                        mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                        for mapp in mappings:
                                            if mapp.sale_order_id.id not in list_mappings_sync_manual:
                                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                                list_mappings_sync_manual.append(mapp.sale_order_id.id)
                                    elif res.status_code == 200:
                                        response_text = res.json()
                                        self.env['bravo.stock.picking.mappings'].import_mapping_bravo(sync_data_line_return_order, response_text, res_command)
                            elif command == 'CreateSucessOrder':
                                sync_data_line_fail_order = []
                                sync_data_line_success_order = []
                                for order in data_sync:
                                    data_line_fail_order = []
                                    data_line_success_order = []
                                    for detail in order['details']:
                                        if detail['quantity_done'] < 0:
                                            detail.pop('product_cost')
                                            detail.pop('so_line_price')
                                            detail.pop('so_line_discount')
                                            detail.pop('so_line_price_subtotal')
                                            data_line_fail_order.append(detail)
                                        else:
                                            data_line_success_order.append(detail)
                                    if len(data_line_success_order) > 0:
                                        line_success_order = ({
                                            'parent_id': order['parent_id'],
                                            'invoice_date': order['invoice_date'],
                                            'sale_name': order['sale_name'],
                                            'details': data_line_success_order
                                        })
                                        sync_data_line_success_order.append(line_success_order)
                                    if len(data_line_fail_order) > 0:
                                        line_fail_order = ({
                                            'parent_id': order['parent_id'],
                                            'invoice_date': order['invoice_date'],
                                            'sale_name': order['sale_name'],
                                            'details': data_line_fail_order
                                        })
                                        sync_data_line_fail_order.append(line_fail_order)
                                ### CreateSucessOrder
                                if len(sync_data_line_success_order) > 0:
                                    res_command = 'CreateSucessOrder'
                                    result = {
                                        "partner": "ODOO",
                                        "command": res_command,
                                    }
                                    result['data'] = sync_data_line_success_order
                                    res = self.env['base.integrate.bravo']._post_data_bravo(
                                        url=bravo_url + '/api/bravowebapi/execute', token=token,
                                        command=res_command, data=json.dumps(result))
                                    # if res.status_code == 200:
                                    #     response_text = res.json()
                                    #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(
                                    #         sync_data_line_success_order, response_text, res_command)
                                    resp = res.json()
                                    if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                        response_text = res.json()
                                        mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                        for mapp in mappings:
                                            if mapp.sale_order_id.id not in list_mappings_sync_manual:
                                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """,(mapp.id,))
                                                list_mappings_sync_manual.append(mapp.sale_order_id.id)
                                    elif res.status_code == 200:
                                        response_text = res.json()
                                        self.env['bravo.stock.picking.mappings'].import_mapping_bravo(sync_data_line_success_order, response_text, res_command)
                                ## CreateFailOrder
                                if len(sync_data_line_fail_order) > 0:
                                    res_command = 'CreateFailOrder'
                                    result = {
                                        "partner": "ODOO",
                                        "command": res_command,
                                    }
                                    result['data'] = sync_data_line_fail_order
                                    res = self.env['base.integrate.bravo']._post_data_bravo(
                                        url=bravo_url + '/api/bravowebapi/execute', token=token,
                                        command=res_command, data=json.dumps(result))
                                    # if res.status_code == 200:
                                    #     response_text = res.json()
                                    #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(
                                    #         sync_data_line_fail_order, response_text, res_command)
                                    resp = res.json()
                                    if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                        response_text = res.json()
                                        mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                        for mapp in mappings:
                                            if mapp.sale_order_id.id not in list_mappings_sync_manual:
                                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                                list_mappings_sync_manual.append(mapp.sale_order_id.id)
                                    elif res.status_code == 200:
                                        response_text = res.json()
                                        self.env['bravo.stock.picking.mappings'].import_mapping_bravo(
                                            sync_data_line_fail_order, response_text, res_command)
                            else:
                                result['data'] = data_sync
                                res = self.env['base.integrate.bravo']._post_data_bravo(
                                    url=bravo_url + '/api/bravowebapi/execute',
                                    token=token, command=command, data=json.dumps(result))
                                # if res.status_code == 200:
                                #     response_text = res.json()
                                #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync,
                                #                                                                   response_text,
                                #                                                                   command)
                                resp = res.json()
                                if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                                    response_text = res.json()
                                    mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                                    for mapp in mappings:
                                        if mapp.sale_order_id.id not in list_mappings_sync_manual:
                                            self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                            list_mappings_sync_manual.append(mapp.sale_order_id.id)
                                elif res.status_code == 200:
                                    response_text = res.json()
                                    self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                        print("post_online_sale_stock_details: %s, count: %s" % (
                            time.time() - start_time, len(list_stock_picking),))
            if count == 10:
                if command == 'CreateSucessOrder':
                    is_create_sucess_order = self.env['ir.config_parameter'].sudo().search([(
                        'key', '=', 'advanced_integrate_bravo.ir_cron_post_online_success_order_bravo_ir_actions_server'
                    )])
                    if is_create_sucess_order:
                        is_create_sucess_order.sudo().write({
                            'value': 'False'
                        })
                elif command == 'CreateReturnOrder':
                    is_create_return_order = self.env['ir.config_parameter'].sudo().search([(
                        'key', '=',
                        'advanced_integrate_bravo.ir_cron_online_sale_success_was_return_bravo_ir_actions_server'
                    )])
                    if is_create_return_order:
                        is_create_return_order.sudo().write({
                            'value': 'False'
                        })
                else:
                    is_create_fail_order = self.env['ir.config_parameter'].sudo().search([(
                        'key', '=', 'advanced_integrate_bravo.ir_cron_online_sale_failed_was_return_bravo_ir_actions_server'
                    )])
                    if is_create_fail_order:
                        is_create_fail_order.sudo().write({
                            'value': 'False'
                        })

        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'push_online_sale_to_bravo',
                'line': '0',
            })

    # Bảng kê chi tiết bill online thành công
    def _format_online_sale_stock_details(self, stock_picks, set_date_to=False):
        res = []
        start_time = time.time()
        count_stock_move = 0
        warehouse_online_id = self.env['stock.warehouse'].sudo().search([('is_location_online', '=', True)], limit=1).lot_stock_id.s_transit_location_id.id
        location_online = self.env['stock.location'].sudo().search([('id', '=', warehouse_online_id), ('s_is_transit_location', '=', True)])
        for stock_pick in stock_picks:
            details = []
            if stock_pick.get('id'):
                stock_move_ids = self.env['stock.move'].sudo().search(
                    [('picking_id', '=', stock_pick.get('id')), ('product_uom_qty', '>', 0)])
                if len(stock_move_ids) > 0:
                    for move in stock_move_ids:
                        if (len(
                                move.location_id.warehouse_id) > 0 and move.location_id.warehouse_id.is_test_location == False) or \
                                (len(
                                    move.location_dest_id.warehouse_id) > 0 and move.location_dest_id.warehouse_id.is_test_location == False):
                            if move.product_id and move.product_id.detailed_type == 'product' and move.product_id:
                                details.append({
                                    "id": move.id,
                                    "location_id": move.location_id.s_code if move.location_id else "",
                                    'location_dest_id': location_online.s_code if location_online.s_code else "",
                                    "product_name": move.product_id.ma_vat_tu if move.product_id.ma_vat_tu else "",
                                    "product_size": move.product_id.get_product_size() if move.product_id.get_product_size() else "00",
                                    "product_barcode": move.product_id.default_code if move.product_id.default_code else "",
                                    "quantity_done": move.quantity_done if move.quantity_done else 0,
                                })
                count_stock_move += len(stock_move_ids)
            if details:
                user_tz = self.env.user.tz or pytz.utc
                tz = pytz.utc.localize(stock_pick.get('date_done')).astimezone(pytz.timezone(user_tz))
                str_tz = datetime.strftime(tz, "%Y-%m-%d")
                if set_date_to and datetime.strptime(str_tz, "%Y-%m-%d") <= datetime.strptime(set_date_to, "%Y-%m-%d"):
                    str_tz = set_date_to
                data = {
                    "parent_id": stock_pick.get('id'),
                    "date_done": str_tz if str_tz else 'None',
                    'sale_name': stock_pick.get('s_origin'),
                    "details": details,
                }
                res.append(data)
        print('_format_online_sale_stock_details: %s, count: %s' % (time.time() - start_time, count_stock_move))
        return res, count_stock_move

    def post_online_sale_stock_details(self, command, set_date, picking_resync_id):
        start_time = time.time()
        try:
            limit = int(self.env['ir.config_parameter'].sudo().get_param('bravo.push.limit', '500'))
            count = 0
            if picking_resync_id:
                count += 9
            list_mappings_sync_manual = []
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                query_stock_picking = self._cr.execute(
                    """SELECT id,date_done,sale_id, s_origin FROM stock_picking 
                    WHERE picking_type_id IN (SELECT id FROM stock_picking_type WHERE code = 'outgoing')
                                  AND state='done'
                                  AND date_done is not null 
                                  AND sale_id IN (SELECT id FROM sale_order WHERE is_magento_order=TRUE OR is_ecommerce_order=TRUE)
                                  AND id NOT IN (SELECT picking_id FROM bravo_stock_picking_mappings WHERE picking_id is not null AND post_api = %s AND (status_code='00' OR need_resync_manual IS TRUE)) LIMIT %s""",
                    ('CreateTransferOnlInv', limit))
                list_stock_picking = self._cr.dictfetchall()
                if picking_resync_id and picking_resync_id not in [res['id'] for res in list_stock_picking]:
                    query_stock_picking = self._cr.execute(
                        """SELECT id,date_done,sale_id, s_origin FROM stock_picking 
                        WHERE picking_type_id IN (SELECT id FROM stock_picking_type WHERE code = 'outgoing')
                                      AND state='done'
                                      AND date_done is not null 
                                      AND sale_id IN (SELECT id FROM sale_order WHERE is_magento_order=TRUE OR is_ecommerce_order=TRUE)
                                      AND id = %s""",
                        (picking_resync_id, ))
                    list_resync = self._cr.dictfetchall()
                    if list_resync:
                        list_stock_picking = list_resync
                if len(list_stock_picking) > 0:
                    start_time_line = time.time()
                    data_unsync = []
                    data_sync = []
                    data, count_stock_move = self._format_online_sale_stock_details(list_stock_picking, set_date)
                    print("_format_online_sale_stock_details: %s, count: %s" % (
                        time.time() - start_time_line, count_stock_move,))
                    if data:
                        for rec in data:
                            for detail in rec['details']:
                                if detail['product_name'] == '' or detail['product_barcode'] == '' or detail[
                                    'quantity_done'] == 0:
                                    data_unsync.append(rec)
                                    break
                            if rec not in data_unsync:
                                data_sync.append(rec)
                    # result = json.dumps({
                    #     "partner": "ODOO",
                    #     "command": command,
                    #     "data": data,
                    # })
                    base_integrate_bravo = self.env['base.integrate.bravo']
                    token = base_integrate_bravo.sudo().get_token_bravo()
                    url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
                    if len(data_unsync) > 0:
                        result = {
                            "partner": "ODOO",
                            "command": command,
                            "data": data_unsync,
                        }
                        response_text = [{
                            'error_message': 'Dữ liệu bị trống (rỗng)',
                            'error_code': 11
                        }]
                        mappings = self.env['bravo.stock.picking.mappings'].sudo().import_mapping_bravo(data_unsync, response_text, command)
                        for mapp in mappings:
                            if mapp.picking_id.id not in list_mappings_sync_manual:
                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s""",(mapp.id,))
                                list_mappings_sync_manual.append(mapp.picking_id.id)
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
                        result = {
                            "partner": "ODOO",
                            "command": command,
                            "data": data_sync,
                        }
                        result = json.dumps(result)
                        res = self.env['base.integrate.bravo']._post_data_bravo(url, token=token, command=command,
                                                                                data=result)
                        # if res.status_code == 200:
                        #     response_text = res.json()
                        #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text,
                        #                                                                   command)
                        resp = res.json()
                        if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                            response_text = res.json()
                            mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                            for mapp in mappings:
                                if mapp.picking_id.id not in list_mappings_sync_manual:
                                    self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """,(mapp.id,))
                                    list_mappings_sync_manual.append(mapp.picking_id.id)
                        elif res.status_code == 200:
                            response_text = res.json()
                            self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data_sync, response_text, command)
                    print("post_online_sale_stock_details: %s, count: %s" % (
                        time.time() - start_time, len(list_stock_picking),))
            if count == 10:
                is_create_transfer_onl_inv = self.env['ir.config_parameter'].sudo().search([(
                    'key', '=', 'advanced_integrate_bravo.ir_cron_post_transfer_online_stock_ir_actions_server'
                )])
                if is_create_transfer_onl_inv:
                    is_create_transfer_onl_inv.sudo().write({
                        'value': 'False'
                    })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': e,
                'func': 'post_online_sale_stock_details',
                'line': '0',
            })

    # Bảng kê chi tiết điều chuyển hàng bán online

    def post_adjustment_stock_details(self, command, set_date):
        start_time = time.time()
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
            limit = int(self.env['ir.config_parameter'].sudo().get_param('bravo.push.limit', '500'))
            count = 0
            list_mappings_sync_manual = []
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                date = datetime.strptime('2023-04-28 00:00:00', '%Y-%m-%d %H:%M:%S')
                query_stock_picking = self._cr.execute(
                    """SELECT id,name,date_done FROM stock_picking 
                    WHERE state='done' 
                    AND date_done is not null 
                    AND date_done >= %s
                    AND sale_id is null 
                    AND (location_id in (SELECT id FROM stock_location WHERE s_is_inventory_adjustment_location=TRUE) 
                    OR location_dest_id in (SELECT id FROM stock_location WHERE s_is_inventory_adjustment_location=TRUE))
                    AND id NOT IN (SELECT picking_id FROM bravo_stock_picking_mappings WHERE picking_id IS NOT NULL AND post_api = %s AND (status_code='00' OR need_resync_manual IS TRUE))
                                       LIMIT %s""", (date, 'CreateDiffInv', 1,))
                list_stock_picking = self._cr.dictfetchall()
                if list_stock_picking:
                    data, count_stock_picking = self._format_adjustment_stock_details(list_stock_picking, set_date)
                    result = {
                        "partner": "ODOO",
                        "command": command,
                        "data": data
                    }
                    result = json.dumps(result)
                    token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                    res = self.env['base.integrate.bravo']._post_data_bravo(url, command=command, token=token, data=result)
                    # if res.status_code == 200:
                    #     response_text = res.json()
                    #     self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data, response_text,
                    #                                                                   command)
                    resp = res.json()
                    if res.status_code != 200 or resp[0].get('error_code') in ['10', '11', '99']:
                        response_text = res.json()
                        mappings = self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data, response_text, command)
                        for mapp in mappings:
                            if mapp.picking_id.id not in list_mappings_sync_manual:
                                self._cr.execute("""UPDATE bravo_stock_picking_mappings SET need_resync_manual = TRUE WHERE id = %s """, (mapp.id,))
                                list_mappings_sync_manual.append(mapp.picking_id.id)
                    elif res.status_code == 200:
                        response_text = res.json()
                        self.env['bravo.stock.picking.mappings'].import_mapping_bravo(data, response_text, command)
                    print('post_internal_stock_details: time:%s, count: %s, lines: %s',
                          (time.time() - start_time, len(list_stock_picking), count_stock_picking))
            if count == 10:
                is_create_diff_inv = self.env['ir.config_parameter'].sudo().search([(
                    'key', '=', 'advanced_integrate_bravo.ir_cron_post_adjustment_stock_details_ir_actions_server'
                )])
                if is_create_diff_inv:
                    is_create_diff_inv.sudo().write({
                        'value': 'False'
                    })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'post_adjustment_stock_details',
                'line': '0',
            })

    def _format_adjustment_stock_details(self, list_stock_picking, set_date_to=False):
        res = []
        details = []
        count_stock_picking = 0
        for picking in list_stock_picking:
            stock_move_ids = self.env['stock.move'].sudo().search([('picking_id', '=', picking.get('id'))])
            for move in stock_move_ids:
                if (len(
                        move.location_id.warehouse_id) > 0 and move.location_id.warehouse_id.is_test_location == False) or \
                        (len(
                            move.location_dest_id.warehouse_id) > 0 and move.location_dest_id.warehouse_id.is_test_location == False):
                    if move.product_id.default_code not in ['1112', '1113', '1114', '1115',
                                                            '003'] and move.product_id.active != False:
                        if move.location_id.usage not in ['inventory'] or move.location_dest_id.usage not in [
                            'inventory']:
                            detail = {
                                'id': move.id,
                                'location_id': '',
                                'product_name': move.product_id.ma_vat_tu if move.product_id.ma_vat_tu else '',
                                "product_size": move.product_id.get_product_size() if move.product_id.get_product_size() else "00",
                                'product_barcode': move.product_id.default_code if move.product_id.default_code else '',
                                'inventory_quantity': 0,
                                'quantity': 0,
                                'inventory_diff_quantity': 0
                            }
                            # todo compute inventory_quantity, quantity, inventory_diff_quantity
                            # tồn thực tế = sổ sách - chênh lệch
                            # xuất: chênh lệch dương
                            # nhập: chênh lệch âm
                            product_quant = 0
                            # move_than = move.product_id.stock_move_ids.filtered(
                            #     lambda l: (l.location_id.id == move.location_id.id or l.location_dest_id.id == move.location_id.id) and l.date > move.date)
                            if move.location_id.usage in ['internal', 'view']:
                                # if not move.inventory_adjustment_quantity:
                                #     quants = move.product_id.stock_quant_ids.filtered(
                                #         lambda r: r.location_id.id == move.location_id.id)
                                #     if quants:
                                #         product_quant = quants.quantity
                                #     for p in move_than:
                                #         if not p.picking_type_id:
                                #             product_quant = p.inventory_adjustment_quantity
                                #         else:
                                #             if p.location_id.usage in ['internal', 'view']:
                                #                 qty_done = p.quantity_done
                                #                 product_quant = product_quant + qty_done
                                #             if p.location_dest_id.usage in ['internal', 'view']:
                                #                 qty_done = -p.quantity_done
                                #                 product_quant = product_quant + qty_done
                                #     total_quantity = product_quant + move.quantity_done
                                #     detail[
                                #         'location_id'] = move.location_id.warehouse_id.code if move.location_id.warehouse_id.code else ''
                                #     detail['quantity'] = product_quant
                                #     detail['inventory_diff_quantity'] = move.quantity_done
                                #     detail['inventory_quantity'] = total_quantity
                                # else:
                                inventory_diff_quantity = move.quantity_done if move.quantity_done else 0
                                detail[
                                    'location_id'] = move.location_id.warehouse_id.code if move.location_id.warehouse_id.code else ''
                                detail['quantity'] = move.inventory_adjustment_quantity
                                detail['inventory_diff_quantity'] = inventory_diff_quantity
                                detail[
                                    'inventory_quantity'] = move.inventory_adjustment_quantity + inventory_diff_quantity
                            elif move.location_dest_id.usage in ['internal', 'view']:
                                # if not move.inventory_adjustment_quantity:
                                #     quants = move.product_id.stock_quant_ids.filtered(
                                #         lambda r: r.location_id.id == move.location_dest_id.id)
                                #     if quants:
                                #         product_quant = quants.quantity
                                #     for p in move_than:
                                #         if not p.picking_type_id:
                                #             product_quant = p.inventory_adjustment_quantity
                                #         else:
                                #             if p.location_id.usage in ['internal', 'view']:
                                #                 qty_done = p.quantity_done
                                #                 product_quant = product_quant + qty_done
                                #             if p.location_dest_id.usage in ['internal', 'view']:
                                #                 qty_done = -p.quantity_done
                                #                 product_quant = product_quant + qty_done
                                #     total_quantity = product_quant - move.quantity_done
                                #     detail[
                                #         'location_id'] = move.location_dest_id.warehouse_id.code if move.location_dest_id.warehouse_id.code else ''
                                #     detail['quantity'] = product_quant
                                #     detail['inventory_diff_quantity'] = -move.quantity_done if move.quantity_done else 0
                                #     detail['inventory_quantity'] = total_quantity
                                # else:
                                inventory_diff_quantity = -move.quantity_done if move.quantity_done else 0
                                detail[
                                    'location_id'] = move.location_dest_id.warehouse_id.code if move.location_dest_id.warehouse_id.code else ''
                                detail['quantity'] = move.inventory_adjustment_quantity
                                detail['inventory_diff_quantity'] = inventory_diff_quantity
                                detail[
                                    'inventory_quantity'] = move.inventory_adjustment_quantity + inventory_diff_quantity
                            # if detail['location_id']:
                            details.append(detail)
            if details:
                user_tz = self.env.user.tz or pytz.utc
                tz = pytz.utc.localize(picking.get('date_done')).astimezone(pytz.timezone(user_tz))
                str_tz = datetime.strftime(tz, "%Y-%m-%d")
                if set_date_to and datetime.strptime(str_tz, "%Y-%m-%d") <= datetime.strptime(set_date_to, "%Y-%m-%d"):
                    str_tz = set_date_to
                head = {
                    "parent_id": picking.get('id') if picking.get('id') else None,
                    "date_done": str_tz if str_tz else None,
                    "details": details,
                }
                res.append(head)
            count_stock_picking += len(stock_move_ids)
        return res, count_stock_picking
