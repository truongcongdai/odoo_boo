from odoo import fields, models, api
from datetime import datetime, timedelta
import json


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    bravo_system_child_id = fields.Integer(string="ID bravo attribute")

    def get_product_size(self):
        if len(self.product_template_attribute_value_ids) > 0:
            for attribute in self.product_template_attribute_value_ids:
                if attribute.attribute_id and attribute.attribute_id.type == 'size':
                    if attribute.product_attribute_value_id:
                        return attribute.product_attribute_value_id.code

    def cron_once_create_diff_inv(self, date, picking_id, move_id):
        # date_done = datetime.strptime(date, '%Y-%m-%d').date()
        # self.env.cr.execute("DROP TABLE stock_diff_inv_outgoing")
        # self.env.cr.execute("DROP TABLE stock_diff_inv_incoming")
        query_stock_move_outcoming = self.env.cr.execute("""
        SELECT incoming.product_id, outgoing.location_id,incoming.location_dest_id, outgoing.product_uom_qty as product_uom_qty_outgoing,incoming.product_uom_qty as product_uom_qty_incoming,incoming.product_uom_qty-outgoing.product_uom_qty as result  FROM stock_diff_inv_outgoing as outgoing
                                            INNER JOIN stock_diff_inv_incoming as incoming ON outgoing.product_id = incoming.product_id
                                            WHERE outgoing.location_id = incoming.location_dest_id;""")
        result_query = self._cr.dictfetchall()
        details = []
        details_child = []
        count = move_id
        start = 0
        end = 100
        for i in range(0, len(result_query)):
            # for res in result_query[start:end]:
            start += 1
            end += 1
            if result_query[i].get('result') != 0 and result_query[i].get('location_id') not in [5, 4, 14, 24, 15, 25,
                                                                                                 16, 26]:
                product_id = self.env['product.product'].sudo().browse(result_query[i].get('product_id'))
                s_location_id = self.env['stock.location'].sudo().browse(result_query[i].get('location_id'))
                if product_id.detailed_type == 'product':
                    inventory_diff_quantity = 0
                    if result_query[i].get('result') > 0:
                        inventory_diff_quantity = result_query[i].get('product_uom_qty_incoming') - result_query[i].get(
                            'product_uom_qty_outgoing')
                    elif result_query[i].get('result') < 0:
                        inventory_diff_quantity = result_query[i].get('product_uom_qty_outgoing') - result_query[i].get(
                            'product_uom_qty_incoming')
                    count += 1
                    details_child.append({
                        'id': count,
                        'location_id': s_location_id.s_code if s_location_id.s_code else '',
                        'product_name': product_id.ma_vat_tu if product_id.ma_vat_tu else '',
                        "product_size": product_id.get_product_size() if product_id.get_product_size() else "00",
                        'product_barcode': product_id.default_code if product_id.default_code else '',
                        'inventory_quantity': abs(result_query[i].get('result')) + inventory_diff_quantity,
                        'quantity': abs(result_query[i].get('result')),
                        'inventory_diff_quantity': inventory_diff_quantity,
                    }, )
            if len(details_child) >= 100:
                details.append(details_child)
                details_child = []
            elif len(result_query[i:]) < 100:
                details.append(details_child)
                break
        count_picking = 1
        if len(details) > 0:
            for detail in details:
                count_picking += 1
                data = {
                    "partner": "ODOO",
                    "command": "CreateDiffInv",
                    "data": [
                        {
                            "parent_id": int(picking_id) + count_picking,
                            "date_done": date,
                            "details": detail
                        },
                    ]

                }
                result = json.dumps(data)
                url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
                token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
                res = self.env['base.integrate.bravo']._post_data_bravo(url, command='CreateDiffInv', token=token,
                                                                        data=result)
                self.env['ir.logging'].sudo().create({
                    'name': 'cron_once_create_diff_inv',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'res',
                    'path': 'url',
                    'message': str(len(detail)) + str(count) + str(data),
                    'func': 'cron_once_create_diff_inv',
                    'line': '0',
                })
        # query_delete_outgoing = self._cr.execute(
        #     """DELETE FROM stock_diff_inv_outgoing;""",)
        # query_delete_incoming = self._cr.execute(
        #     """DELETE FROM stock_diff_inv_incoming;""", )

    def _cron_sync_stock_available_export_inv(self, date, picking_id, move_id):
        date_time = datetime.strptime('2023-06-04 00:00:00', '%Y-%m-%d %H:%M:%S')
        query_product_move = self.env.cr.execute("""select product_id from stock_move where create_date < %s 
            and picking_id in (SELECT id FROM stock_picking WHERE bravo_name is not null) group by product_id""", (date_time,))
        result_query_product_move = [res[0] for res in self._cr.fetchall()]
        count = move_id
        details_child = []
        if len(result_query_product_move) > 0:
            for p in result_query_product_move:
                query_stock_move = self.env.cr.execute("""select id, location_id, location_dest_id, picking_id from stock_move where 
                picking_id in (select id from stock_picking where bravo_name is not null) and product_id = %s""", (p,))
                result_query_stock_move = self._cr.dictfetchall()
                if len(result_query_stock_move) > 0:
                    qty_diff = 0
                    product_id = False
                    s_location_ids = []
                    s_location_dest_ids = []
                    for move in result_query_stock_move:
                        product_id = self.env['product.product'].sudo().search([('id', '=', p)])
                        stock_move_id = self.env['stock.move'].sudo().search([('id', '=', move.get('id'))])
                        stock_in = 0
                        stock_out = 0
                        s_location_ids.append(move.get('location_id'))
                        s_location_dest_ids.append(move.get('location_dest_id'))
                        for rec in stock_move_id:
                            if rec.location_id.id not in [4,]:
                                stock_out += rec.product_uom_qty
                            else:
                                stock_in += rec.product_uom_qty
                        qty_diff = stock_in - stock_out
                    if qty_diff != 0:
                        if list(set(s_location_ids))[0] not in [4,]:
                            location_id = self.env['stock.location'].sudo().search([('id', '=', list(set(s_location_ids))[0])])
                            quantity = product_id.stock_quant_ids.filtered(lambda r: r.location_id.id == list(set(s_location_ids))[0]).quantity
                        else:
                            location_id = self.env['stock.location'].sudo().search([('id', '=', list(set(s_location_dest_ids))[0])])
                            quantity = product_id.stock_quant_ids.filtered(lambda r: r.location_id.id == list(set(s_location_dest_ids))[0]).quantity
                        if quantity > 0:
                            count += 1
                            details_child.append({
                                'id': count,
                                'location_id': location_id.s_code if location_id.s_code else '',
                                'product_name': product_id.ma_vat_tu if product_id.ma_vat_tu else '',
                                "product_size": product_id.get_product_size() if product_id.get_product_size() else "00",
                                'product_barcode': product_id.default_code if product_id.default_code else '',
                                'inventory_quantity': quantity + qty_diff,
                                'quantity': quantity,
                                'inventory_diff_quantity': qty_diff,
                            })
            data = {
                "partner": "ODOO",
                "command": "CreateDiffInv",
                "data": [
                    {
                        "parent_id": int(picking_id),
                        "date_done": date,
                        "details": details_child
                    },
                ]
            }
            result = json.dumps(data)
            url = self.env['ir.config_parameter'].sudo().get_param('bravo.url', '') + '/api/bravowebapi/execute'
            token = self.env['base.integrate.bravo'].sudo().get_token_bravo()
            res = self.env['base.integrate.bravo']._post_data_bravo(url, command='CreateDiffInv', token=token, data=result)
            response_text = res.json()
            self.env['ir.logging'].sudo().create({
                'name': '_cron_sync_stock_available_export_inv',
                'type': 'server',
                'dbname': 'boo',
                'level': 'res',
                'path': 'url',
                'message': str(response_text) + str(data),
                'func': '_cron_sync_stock_available_export_inv',
                'line': '0',
            })
