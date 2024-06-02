import json
import logging
import time
import traceback
from copy import deepcopy
from urllib.parse import urljoin

from odoo import api, fields, models
from ..tools.api_wrapper import _create_log
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = ['stock.quant']

    to_update_magento = fields.Boolean(
        string='Update Magento?',
        compute='_compute_to_update_magento',
        compute_sudo=True
    )

    @api.depends(
        'location_id',
        'location_id.warehouse_id',
        'product_id',
        'product_id.sync_push_magento'
    )
    def _compute_to_update_magento(self):
        for r in self:
            to_update_magento = False
            if r.product_id.sync_push_magento and r.location_id.warehouse_id.m2_stock_ids and r.location_id.warehouse_id.status_stock_warehouse:
                to_update_magento = True
            r.to_update_magento = to_update_magento

    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super(StockQuant, self).create(vals_list)
    #     res._magento_update_stock_qty()
    #     return res

    def create(self, vals):
        keys_to_check = ('quantity', 'reserved_quantity')
        res = super(StockQuant, self).create(vals)
        if any([key in vals for key in keys_to_check]):
            if not res.product_id.need_sync_m2_stock and res.product_tmpl_id.sync_push_magento:
                res.product_id.need_sync_m2_stock = True
        return res

    def write(self, vals):
        keys_to_check = ('quantity', 'reserved_quantity')
        res = super(StockQuant, self).write(vals)
        if any([key in vals for key in keys_to_check]):
            for rec in self:
                if rec.product_tmpl_id.sync_push_magento:
                    rec.product_id.need_sync_m2_stock = True
        return res

    # def cron_synchronizing_stock_qty(self):
    #     stock_quant = self.search([('product_tmpl_id.sync_push_magento', '=', True),
    #                                ('product_tmpl_id.check_sync_product', '=', True),
    #                                ('product_tmpl_id.check_sync_qty', '=', False)])
    #     for r in stock_quant:
    #         r._magento_update_stock_qty()

    @api.model
    def _get_magento_update_stock_qty_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url, f'/rest/{magento_odoo_bridge.store_code}/V1/inventory/source-items')

    def _build_magento_update_stock_qty_data(self):
        self = self.filtered(lambda r: r.to_update_magento)
        source_items = []
        all_quants = self.search([])
        for product in self.product_id:
            # TODO: @nhatnm
            # [According to Magento 2x dev (Jun)] 1: In Stock / 2: Out of Stock
            # Out of Stock: even if has stock, not available for selling
            status = 1
            for code_name in self.location_id.warehouse_id.mapped('source_code_name'):
                correct_quant = all_quants.filtered(
                    lambda r: r.product_id.id == product.id and
                              r.location_id.warehouse_id.source_code_name == code_name and
                              r.location_id.usage != 'inventory'
                )
                quantity = sum(correct_quant.mapped('quantity'))
                source_items.append({
                    'sku': product.default_code,
                    'source_code': code_name,
                    'quantity': quantity,
                    'status': status
                })
        return {
            'sourceItems': source_items
        }

    @api.model
    def get_m2_sdk(self):
        return self.env.ref('magento2x_odoo_bridge.magento2x_channel').sudo().get_magento2x_sdk()['sdk']

    def _magento_update_stock_qty(self):
        self = self.filtered(lambda r: r.to_update_magento)
        if not self:
            return
        try:
            sdk = self.get_m2_sdk()
            url = self._get_magento_update_stock_qty_url()
            data = json.dumps(self._build_magento_update_stock_qty_data())
            resp = sdk._post_data(url=url, data=data)
            if resp.get('message'):
                _logger.error(resp.get('message'))
                # raise ValidationError(resp.get('message'))
                # _create_log(
                #     name=resp['message'],
                #     message=f'{fields.Datetime.now().isoformat()} POST {url}\n' +
                #             f'data={data}\n' +
                #             f'response={resp}\n',
                #     func='_magento_update_stock_qty'
                # )
            else:
                self.product_tmpl_id.write({'check_sync_qty': True})
                self.env.cr.commit()
        except Exception as e:
            _logger.error(e.args)
            # raise ValidationError(e.args)
            # _create_log(name='magento_update_stock_qty', message=e.args, func='_magento_update_stock_qty')

    def _get_magento_update_reserved_qty_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url, f'/rest/{magento_odoo_bridge.store_code}/V1/reservation/add')

    def magento_push_reserved_qty(self, need_sync_product_product_ids):
        data_reserved_qty = []
        sync_stock_move = []
        for need_sync_product_product_id in need_sync_product_product_ids:
            if need_sync_product_product_id.get('id'):
                s_stock_move_ids = self.env['stock.move'].sudo().search([
                    ('product_id', '=', need_sync_product_product_id['id']), ('s_m2_reserved_quantity', '!=', 0),
                    ('is_push_m2_reserved_quantity', '=', False),('s_disable_push_m2_reserved_quantity', '=', False)])
                if s_stock_move_ids:
                    for stock_move in s_stock_move_ids:
                        source = None
                        if stock_move.location_id:
                            location_id = stock_move.location_id
                            if location_id.warehouse_id:
                                if location_id.warehouse_id.lot_stock_id.id == location_id.id:
                                    source = location_id.warehouse_id.source_code_name
                                else:
                                    source = location_id.s_code
                        if source:
                            data_reserved_qty.append({
                                "stock_id": 2,
                                "sku": stock_move.product_id.default_code,
                                "source": source,
                                "quantity": stock_move.s_m2_reserved_quantity,
                                "metadata": str(stock_move.reference) + "-" + str(stock_move.state) + ": " + str(
                                    stock_move.location_id.display_name) + " - " + str(
                                    stock_move.location_dest_id.display_name)
                            })
                            sync_stock_move.append({'id': stock_move.id, 'state': stock_move.state})
        if data_reserved_qty:
            try:
                sdk = self.get_m2_sdk()
                url = self._get_magento_update_reserved_qty_url()
                resp = sdk._post_data(url=url, data=json.dumps(data_reserved_qty))
                # resp = {'test': 'success'}
                if resp.get('message'):
                    self.env['ir.logging'].sudo().create({
                        'type': 'server',
                        'name': 'cron_sync_reserved_qty error',
                        'path': 'path',
                        'line': 'line',
                        'func': 'func',
                        'message': str(resp.get('message')) + str(data_reserved_qty)
                    })
                else:
                    if len(sync_stock_move) > 0:
                        for move in sync_stock_move:
                            if move.get('id') and move.get('state'):
                                self._cr.execute(
                                    'update stock_move set  is_push_m2_reserved_quantity = TRUE, s_pushed_m2_reserved_state=%s where id = %s',
                                    (move.get('state'),move.get('id'),))
                            else:
                                self.env['ir.logging'].sudo().create({
                                    'type': 'server',
                                    'name': 'cron_sync_reserved_qty error',
                                    'path': 'path',
                                    'line': 'line',
                                    'func': 'func',
                                    'message': str(resp.get('message')) + str(move)
                                })
                    self.env['ir.logging'].sudo().create({
                        'type': 'server',
                        'name': 'cron_sync_reserved_qty info',
                        'path': 'path',
                        'line': 'line',
                        'func': 'func',
                        'message': str(resp.get('message')) + str(data_reserved_qty)
                    })
            except Exception as e:
                self.env['ir.logging'].sudo().create({
                    'type': 'server',
                    'name': 'cron_sync_reserved_qty error',
                    'path': 'path',
                    'line': 'line',
                    'func': 'func',
                    'message': str(e)
                })

    def cron_synchronizing_stock_qty(self):
        try:
            start_time = time.time()
            need_sync_product_product_ids = self._cr.execute("""select id,default_code from product_product where need_sync_m2_stock=true and default_code is not null""")
            need_sync_product_product_ids = self._cr.dictfetchall()
            if len(need_sync_product_product_ids) > 0:
                need_sync_product_product_sku_dict = {}
                for e in need_sync_product_product_ids:
                    need_sync_product_product_sku_dict[e['id']] = e['default_code']
                need_sync_product_product_id_dict = {}
                for e in need_sync_product_product_ids:
                    need_sync_product_product_id_dict[e['default_code']] = e['id']

                all_magento_warehouse = self.env['stock.warehouse'].search([('status_stock_warehouse', '=', True)])
                magento_location_dict = {}
                for e in all_magento_warehouse:
                    magento_location_dict[e.lot_stock_id.id] = {
                        'quantity': 0,
                        'warehouse_code': e.source_code_name
                    }
                location_domain_list = [str(e) for e in all_magento_warehouse.lot_stock_id.ids]
                location_domain_str = '(' + ','.join(location_domain_list) + ')'
                product_domain_list = [str(e['id']) for e in need_sync_product_product_ids]
                product_domain_str = '(' + ','.join(product_domain_list) + ')'
                all_stock_quant = self._cr.execute(
                    'select location_id,product_id,quantity from stock_quant where location_id in ' + location_domain_str + ' and product_id in ' + product_domain_str)
                all_stock_quant = self._cr.dictfetchall()
                product_stock_dict = {}
                for product in need_sync_product_product_ids:
                    product_stock_dict[product['id']] = deepcopy(magento_location_dict)
                for stock_quant in all_stock_quant:
                    if stock_quant['product_id'] not in product_stock_dict:
                        product_stock_dict[stock_quant['product_id']] = deepcopy(magento_location_dict)
                    product_stock_dict[stock_quant['product_id']][stock_quant['location_id']]['quantity'] += \
                        stock_quant['quantity'] if stock_quant['quantity'] else 0
                final_magento_json_data = []
                for product_id in product_stock_dict:
                    product_sale_ok = False
                    product_record = self.env['product.product'].sudo().search(
                        [('default_code', '=', need_sync_product_product_sku_dict[product_id])], limit=1)
                    if product_record:
                        product_sale_ok = product_record.sale_ok
                    for location_id in product_stock_dict[product_id]:
                        final_magento_json_data.append({
                            "sku": need_sync_product_product_sku_dict[product_id],
                            "source_code": product_stock_dict[product_id][location_id]['warehouse_code'],
                            "quantity": product_stock_dict[product_id][location_id]['quantity'],
                            "status": 1 if product_sale_ok else 0
                        })

                def list_split(listA, n):
                    for x in range(0, len(listA), n):
                        every_chunk = listA[x: n + x]

                        # if len(every_chunk) < n:
                        #     every_chunk = every_chunk + \
                        #                   [None for y in range(n - len(every_chunk))]
                        yield every_chunk

                final_magento_json_data_list = []
                updated_product_product_ids = []
                if len(final_magento_json_data) > 5000:
                    final_magento_json_data_list = list(list_split(final_magento_json_data, 5000))
                else:
                    final_magento_json_data_list = [final_magento_json_data]
                for e in final_magento_json_data_list:
                    try:
                        sdk = self.get_m2_sdk()
                        url = self._get_magento_update_stock_qty_url()
                        data = json.dumps({
                            'sourceItems': e
                        })
                        resp = sdk._post_data(url=url, data=data)
                        if resp.get('message'):
                            self.env['ir.logging'].sudo().create({
                                'type': 'server',
                                'name': 'cron_synchronizing_stock_qty error',
                                'path': 'path',
                                'line': 'line',
                                'func': 'func',
                                'message': str(resp.get('message'))
                            })
                            # raise ValidationError(resp.get('message'))
                        else:
                            for i in e:
                                if need_sync_product_product_id_dict[i['sku']] not in updated_product_product_ids:
                                    updated_product_product_ids.append(need_sync_product_product_id_dict[i['sku']])
                    except Exception as e:
                        error = traceback.format_exc()
                        self.env['ir.logging'].sudo().create({
                            'type': 'server',
                            'name': 'cron_synchronizing_stock_qty error',
                            'path': 'path',
                            'line': 'line',
                            'func': 'func',
                            'message': str(error)
                        })
                        # raise ValidationError(e.args)
                if len(updated_product_product_ids) > 0:
                    product_domain_list = [str(e) for e in updated_product_product_ids]
                    product_domain_str = '(' + ','.join(product_domain_list) + ')'
                    self._cr.execute('update product_product set  need_sync_m2_stock = false where id in ' + product_domain_str)
                    self.env['ir.logging'].sudo().create({
                        'type': 'server',
                        'name': 'cron_synchronizing_stock_qty log',
                        'path': 'path',
                        'line': 'line',
                        'func': 'func',
                        'message': 'cron_synchronizing_stock_qty update ' + str(len(updated_product_product_ids)) + ' product.product in ' + str(time.time() - start_time)
                    })
                self.magento_push_reserved_qty(need_sync_product_product_ids)
        except Exception as ex:
            error = traceback.format_exc()
            self.env['ir.logging'].sudo().create({
                'type': 'server',
                'name': 'cron_synchronizing_stock_qty error',
                'path': 'path',
                'line': 'line',
                'func': 'func',
                'message': str(error)
            })
