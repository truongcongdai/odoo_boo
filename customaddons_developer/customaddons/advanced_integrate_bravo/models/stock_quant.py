from odoo import models, fields, api
import json
import pytz
from datetime import datetime
from odoo.http import request, _logger
import time

class StockQuant(models.Model):
    _inherit = ['stock.quant']

    check_sync_stock_transit = fields.Boolean(default=False)

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res = super(StockQuant, self)._get_inventory_move_values(qty, location_id, location_dest_id, out)
        res.update({'inventory_adjustment_quantity': self.inventory_quantity})
        return res

    @api.model
    def create(self, vals):
        res = super(StockQuant, self).create(vals)
        if 'location_id' in vals.keys() and 'product_id' in vals.keys():
            stock_location = self.env['stock.location'].sudo().search([('id', '=', vals.get('location_id'))], limit=1)
            if stock_location.usage == 'internal' and stock_location.s_is_transit_location == True:
                transit_stock_quant_id = self.env['s.transit.stock.quant'].sudo().search([
                    ('product_id', '=', vals.get('product_id')), ('location_id', '=', vals.get('location_id'))], limit=1)
                if not transit_stock_quant_id:
                    self.env['s.transit.stock.quant'].sudo().create(vals)
                else:
                    transit_stock_quant_id.sudo().write(vals)
        return res

    def write(self, vals):
        res = super(StockQuant, self).write(vals)
        keys_to_check = ('quantity', 'available_quantity')
        for r in self:
            if r.location_id.usage == 'internal' and r.location_id.s_is_transit_location == True and any([key in vals for key in keys_to_check]):
                transit_stock_quant_id = self.env['s.transit.stock.quant'].sudo().search([
                    ('product_id', '=', r.product_id.id), ('location_id', '=', r.location_id.id)], limit=1)
                if transit_stock_quant_id:
                    value = {
                        'to_sync_bravo': False,
                        'available_quantity': r.available_quantity,
                        'quantity': r.quantity,
                        'inventory_quantity_auto_apply': r.inventory_quantity_auto_apply
                    }
                    transit_stock_quant_id.sudo().write(value)
                else:
                    self.env['s.transit.stock.quant'].sudo().create({
                        'inventory_quantity': r.inventory_quantity,
                        'inventory_quantity_set': r.inventory_quantity_set,
                        'location_id': r.location_id.id if r.location_id else False,
                        'product_id': r.product_id.id if r.product_id else False,
                        'available_quantity': r.available_quantity,
                        'quantity': r.quantity,
                        'inventory_quantity_auto_apply': r.inventory_quantity_auto_apply
                    })
        return res

    def unlink(self):
        for r in self:
            if r.location_id.usage == 'internal' and r.location_id.s_is_transit_location == True:
                s_stock_quant_id = self.env['s.transit.stock.quant'].sudo().search([
                    ('product_id', '=', r.product_id.id), ('location_id', '=', r.location_id.id)], limit=1)
                if s_stock_quant_id:
                    s_stock_quant_id.sudo().write({
                        'inventory_quantity': 0,
                        'available_quantity': 0,
                        'inventory_diff_quantity': 0,
                        'reserved_quantity': 0,
                        'quantity': 0,
                        'inventory_quantity_auto_apply': 0,
                        'to_sync_bravo': False
                    })
        return super(StockQuant, self).unlink()

    def _cron_compute_stock_quant_to_transit_stock_quant(self):
        stock_quant_ids = self.sudo().search([('check_sync_stock_transit', '=', False), ('location_id.s_is_transit_location', '=', True)])
        transit_obj = self.env['s.transit.stock.quant'].sudo()
        for stock_quant_id in stock_quant_ids:
            transit_stock_quant_id = transit_obj.search([('product_id', '=', stock_quant_id.product_id.id),
                ('location_id', '=', stock_quant_id.location_id.id)], limit=1)
            quantity = stock_quant_id.quantity
            vals = {
                'quantity': quantity if quantity else 0,
                'product_id': stock_quant_id.product_id.id,
                'location_id': stock_quant_id.location_id.id,
                'available_quantity': quantity if quantity else 0,
                'to_sync_bravo': False
            }
            if transit_stock_quant_id:
                transit_stock_quant_id.unlink()
                transit_stock_quant_id.create(vals)
            else:
                transit_obj.create(vals)

    def _compute_stock_transit_online(self):
        ###Đơn SO và return của SO
        query_so = self._cr.execute("""
            SELECT id FROM sale_order WHERE is_magento_order IS TRUE OR (return_order_id IS NOT NULL AND return_order_id IN (SELECT id FROM sale_order WHERE is_magento_order IS TRUE))
        """)
        result_query_so = [res[0] for res in self._cr.fetchall()]
        ###Stock picking
        query_picking = self._cr.execute("""
            SELECT id FROM stock_picking WHERE state='done' AND sale_id IS NOT NULL AND sale_id IN %s
        """, (tuple(result_query_so),))
        result_query_picking = [res[0] for res in self._cr.fetchall()]
        ###Sản phẩm
        query_product_transit_location_online = self._cr.execute("""
            SELECT product_id FROM stock_move WHERE picking_id IN %s
                AND (location_id IN (SELECT id FROM stock_location WHERE usage in ('customer')) 
                OR location_dest_id IN (SELECT id FROM stock_location WHERE usage in ('customer')))
                GROUP BY product_id """, (tuple(result_query_picking),))
        product_ids = [res[0] for res in self._cr.fetchall()]
        ###Stock move
        query_move_transit_location_online = self._cr.execute("""
            SELECT id FROM stock_move WHERE picking_id IN %s
                AND (location_id IN (SELECT id FROM stock_location WHERE usage in ('customer')) 
                OR location_dest_id IN (SELECT id FROM stock_location WHERE usage in ('customer')))""", (tuple(result_query_picking),))
        result_move = [res[0] for res in self._cr.fetchall()]
        if len(product_ids) > 0:
            warehouse_online_id = self.env['stock.warehouse'].sudo().search([('is_location_online', '=', True)], limit=1).lot_stock_id.s_transit_location_id.id
            location_online = self.env['stock.location'].sudo().search([('id', '=', warehouse_online_id), ('s_is_transit_location', '=', True)], limit=1)
            product_product_ids = self.env['product.product'].sudo().search([('id', 'in', product_ids), ('detailed_type', '=', 'product')])
            for product_id in product_product_ids:
                stock_move_ids = self.env['stock.move'].sudo().search(
                    [('id', 'in', result_move), ('sale_line_id', '!=', False), ('product_id', '=', product_id.id)])
                stock_qty = 0
                for move in stock_move_ids:
                    sale_order_status = move.picking_id.sale_id.sale_order_status
                    if sale_order_status in ('dang_xu_ly', 'dang_giao_hang'):
                        stock_qty += move.product_uom_qty
                transit_obj = self.env['s.transit.stock.quant'].sudo()
                stock_transit = transit_obj.search([('product_id', '=', product_id.id), ('location_id', '=', location_online.id)], limit=1)
                vals = {
                    'location_id': location_online.id,
                    'product_id': product_id.id,
                    'available_quantity': stock_qty,
                    'quantity': stock_qty,
                    'to_sync_bravo': False
                }
                if not stock_transit and location_online:
                    transit_obj.create(vals)
                elif stock_transit and location_online:
                    stock_transit.unlink()
                    transit_obj.create(vals)

    def _cron_sync_inventory_diff_adjusment(self):
        start_time = time.time()
        try:
            count = 0
            # limit = int(self.env['ir.config_parameter'].sudo().get_param('bravo.push.limit', '500'))
            limit = 500
            while count < 10 and (time.time() - start_time) < 50:
                ref_parameter = self.env.ref('advanced_integrate_bravo.stored_id_diff_transit_inv_bravo_config_parameter')
                child_id = int(ref_parameter.value)
                details_child = []
                data_unsync = []
                count += 1
                query_transit_location = self._cr.execute("""
                    SELECT id FROM s_transit_stock_quant WHERE to_sync_bravo IS FALSE LIMIT %s""", (limit,))
                result_query = [res[0] for res in self._cr.fetchall()]
                if len(result_query) > 0:
                    for res_id in result_query:
                        stock = self.env['s.transit.stock.quant'].sudo().browse(res_id)
                        child_id += 1
                        inventory_quantity = stock.quantity if stock.quantity else 0
                        quantity = stock.quantity if stock.quantity else 0
                        res = {
                            'id': child_id,
                            'location_id': stock.location_id.s_code if stock.location_id.s_code else '',
                            'product_name': stock.product_id.ma_vat_tu if stock.product_id.ma_vat_tu else '',
                            "product_size": stock.product_id.get_product_size() if stock.product_id.get_product_size() else "00",
                            'product_barcode': stock.product_id.default_code if stock.product_id.default_code else '',
                            'inventory_quantity': inventory_quantity,
                            'quantity': quantity,
                            'inventory_diff_quantity': inventory_quantity - quantity,
                        }
                        if stock.product_id.default_code == '':
                            data_unsync.append(res)
                        else:
                            details_child.append(res)
                    if len(data_unsync) > 0:
                        response_text = [{
                            'error_message': 'Dữ liệu bị trống (rỗng)',
                            'error_code': 11
                        }]
                        self.env['ir.logging'].sudo().create({
                            'name': 'CreateDiffInv',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'message': str(response_text) + str(data_unsync),
                            'path': 'url',
                            'func': '_post_data_bravo',
                            'line': '0',
                        })
                    if len(details_child) > 0:
                        user_tz = self.env.user.tz or pytz.utc
                        time_now = fields.Datetime.now()
                        datetime_tz = datetime.strptime(
                            datetime.strftime(pytz.utc.localize(time_now).astimezone(pytz.timezone(user_tz)), "%Y-%m-%d %H:%M:%S"),
                            '%Y-%m-%d %H:%M:%S')
                        str_tz = datetime.strftime(datetime_tz, "%Y-%m-%d")
                        data = {
                            "partner": "ODOO",
                            "command": "CreateDiffInv",
                            "data": [
                                {
                                    "parent_id": 1,
                                    "date_done": str_tz,
                                    "details": details_child
                                },
                            ]
                        }
                        result = json.dumps(data)
                        url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
                        token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                        res = self.env['base.integrate.bravo']._post_data_bravo(url, command='CreateDiffInv', token=token, data=result)
                        if res.status_code == 200:
                            self._cr.execute(
                                """UPDATE s_transit_stock_quant SET to_sync_bravo = TRUE WHERE id in %s """,
                                (tuple(result_query),))
                            ref_parameter.sudo().write({
                                'value': child_id
                            })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': 'CreateDiffInventoryTransit',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'post_adjustment_stock_details',
                'line': '0',
            })

    def _sync_stock_to_balance_stock_bravo(self):
        try:
            product_in_stock_move = self._cr.execute("""
                SELECT product_id FROM stock_move WHERE product_id IS NOT NULL GROUP BY product_id
            """)
            result_query = [item[0] for item in self._cr.fetchall()]
            ref_parameter = self.env.ref('advanced_integrate_bravo.stored_id_diff_transit_inv_bravo_config_parameter')
            child_id = int(ref_parameter.value)

            product_ids = self.env['product.product'].sudo().search([('detailed_type', '=', 'product'), ('id', 'in', result_query)])
            warehouse_ids = self.env['stock.warehouse'].sudo().search([('is_test_location', '=', True)]).mapped('id')
            stock_location_ids = self.env['stock.location'].sudo().search([('usage', '=', 'internal'),
                                                                       ('s_is_transit_location', '=', False),
                                                                       ('s_is_inventory_adjustment_location', '=', False),
                                                                       ('scrap_location', '=', False),
                                                                       ('return_location', '=', False),
                                                                       ]).filtered(lambda stock: stock.warehouse_id.id not in warehouse_ids).mapped('id')
            if len(product_ids) > 0:
                details = []
                details_child = []
                data_unsync = []
                start_time = time.time()
                for i in range(0, len(product_ids)):
                # for product in product_ids:
                    query_stock_move_line = self._cr.execute("""
                        SELECT location_id, location_dest_id FROM stock_move_line WHERE product_id = %s AND state='done'
                            AND (location_id IN %s OR location_dest_id IN %s)
                    """, (product_ids[i].id, tuple(stock_location_ids), tuple(stock_location_ids)))
                    result_query_move_line = self._cr.dictfetchall()
                    stock_move_line = self.env['stock.move.line'].sudo().search([('product_id', '=', product_ids[i].id), ('state', '=', 'done')])
                    if len(result_query_move_line) > 0:
                        match_location_id = []
                        un_match_location = []
                        valid_stock_quant_ids = product_ids[i].stock_quant_ids.filtered(lambda s: s.location_id.id in stock_location_ids) ### stock_quant
                        location_ids = [item['location_id'] for item in result_query_move_line]
                        location_dest_ids = [item['location_dest_id'] for item in result_query_move_line]
                        full_location_id = list(set(location_ids + location_dest_ids))  ##location truy vết
                        # So sánh tồn kho bên truy vết có ở bên số lượng tồn kho không
                        for valid_quant in valid_stock_quant_ids:
                            # if valid_quant.location_id.id == value_id and valid_quant not in un_match_location and valid_quant not in match_location_id:
                            #     match_location_id.append(valid_quant)
                            if valid_quant.location_id.id not in full_location_id and valid_quant not in un_match_location and valid_quant not in match_location_id:
                                un_match_location.append(valid_quant)
                        #
                        for value_id in full_location_id:
                            if value_id in stock_location_ids:
                                final_quantity = 0
                                quantity = 0
                                valid_stock_line = stock_move_line.filtered(lambda l: l.location_id.id == value_id or l.location_dest_id.id == value_id)
                                valid_stock_quantity = product_ids[i].stock_quant_ids.filtered(lambda stock: stock.location_id.id == value_id)
                                if valid_stock_line:
                                    for qty_valid in valid_stock_line:
                                        if qty_valid.location_id.id == value_id:
                                            quantity -= qty_valid.qty_done
                                        elif qty_valid.location_dest_id.id == value_id:
                                            quantity += qty_valid.qty_done
                                if valid_stock_quantity:
                                    if valid_stock_quantity.quantity == quantity:
                                        final_quantity = quantity
                                        if final_quantity < 0:
                                            final_quantity = 0
                                    else:
                                        final_quantity = valid_stock_quantity.quantity
                                child_id += 1
                                s_location_id = self.env['stock.location'].sudo().browse(value_id)
                                vals = {
                                    'id': child_id,
                                    'location_id': s_location_id.s_code,
                                    'product_name': product_ids[i].ma_vat_tu if product_ids[i].ma_vat_tu else '',
                                    "product_size": product_ids[i].get_product_size() if product_ids[i].get_product_size() else "00",
                                    'product_barcode': product_ids[i].default_code if product_ids[i].default_code else '',
                                    'inventory_quantity': final_quantity,
                                    'quantity': final_quantity,
                                    'inventory_diff_quantity': final_quantity - final_quantity,
                                }
                                if product_ids[i].default_code == '':
                                    data_unsync.append(vals)
                                else:
                                    details_child.append(vals)
                        if len(un_match_location) > 0:
                            for record in un_match_location:
                                child_id += 1
                                vals = {
                                    'id': child_id,
                                    'location_id': record.location_id.s_code,
                                    'product_name': product_ids[i].ma_vat_tu if product_ids[i].ma_vat_tu else '',
                                    "product_size": product_ids[i].get_product_size() if product_ids[i].get_product_size() else "00",
                                    'product_barcode': product_ids[i].default_code if product_ids[i].default_code else '',
                                    'inventory_quantity': record.quantity,
                                    'quantity': record.quantity,
                                    'inventory_diff_quantity': 0,
                                }
                                if product_ids[i].default_code == '':
                                    data_unsync.append(vals)
                                else:
                                    details_child.append(vals)
                        if len(details_child) >= 500:
                            details.append(details_child)
                            details_child = []
                check_time = time.time() - start_time
                if len(data_unsync) > 0:
                    response_text = [{
                        'error_message': 'Dữ liệu bị trống (rỗng)',
                        'error_code': 11
                    }]
                    self.env['ir.logging'].sudo().create({
                        'name': 'CreateDiffInv',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'message': str(response_text) + str(data_unsync),
                        'path': 'url',
                        'func': '_post_data_bravo',
                        'line': '0',
                    })
                if len(details) > 0:
                    for detail in details:
                        user_tz = self.env.user.tz or pytz.utc
                        time_now = fields.Datetime.now()
                        datetime_tz = datetime.strptime(
                            datetime.strftime(pytz.utc.localize(time_now).astimezone(pytz.timezone(user_tz)),
                                              "%Y-%m-%d %H:%M:%S"),
                            '%Y-%m-%d %H:%M:%S')
                        str_tz = datetime.strftime(datetime_tz, "%Y-%m-%d")
                        data = {
                            "partner": "ODOO",
                            "command": "CreateDiffInv",
                            "data": [
                                {
                                    "parent_id": 1,
                                    "date_done": str_tz,
                                    "details": detail
                                },
                            ]
                        }
                        result = json.dumps(data)
                        url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
                        token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                        res = self.env['base.integrate.bravo']._post_data_bravo(url, command='CreateDiffInv',
                                                                                token=token, data=result)
                        if res.status_code == 200:
                            ref_parameter.sudo().write({
                                'value': child_id
                            })
                            response_text = res.json()
                            self.env['ir.logging'].sudo().create({
                                'name': '_phiếu kiểm kê cân tồn kho Odoo-Bravo',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'res',
                                'path': 'url',
                                'message': str(response_text) + str(data),
                                'func': '_sync_stock_to_balance_stock_bravo',
                                'line': '0',
                            })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': '_phiếu kiểm kê cân tồn kho Odoo-Bravo',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': '_sync_stock_to_balance_stock_bravo',
                'line': '0',
            })